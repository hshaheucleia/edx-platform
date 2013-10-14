"""
Utility functions for transcripts.
"""
import json
import HTMLParser
import StringIO
import requests
import logging
from pysrt import SubRipTime, SubRipItem, SubRipFile
from lxml import etree

from cache_toolbox.core import del_cached_content
from django.conf import settings

from xmodule.exceptions import NotFoundError
from xmodule.contentstore.content import StaticContent
from xmodule.contentstore.django import contentstore
from xmodule.modulestore import Location
from xmodule.modulestore.inheritance import own_metadata

from .utils import get_modulestore

log = logging.getLogger(__name__)


class TranscriptsGenerationException(Exception):
    pass

def generate_subs(speed, source_speed, source_subs):
    """
    Generate transcripts from one speed to another speed.

    Args:
    `speed`: float, for this speed subtitles will be generated,
    `source_speed`: float, speed of source_subs
    `soource_subs`: dict, existing subtitles for speed `source_speed`.

    Returns:
    `subs`: dict, actual subtitles.
    """
    if speed == source_speed:
        return source_subs

    coefficient = 1.0 * speed / source_speed
    subs = {
        'start': [
            int(round(timestamp * coefficient)) for
            timestamp in source_subs['start']
        ],
        'end': [
            int(round(timestamp * coefficient)) for
            timestamp in source_subs['end']
        ],
        'text': source_subs['text']}
    return subs


def save_subs_to_store(subs, subs_id, item):
    """
    Save transcripts into `StaticContent`.

    Args:
    `subs_id`: str, subtitles id
    `item`: video module instance

    Returns: location of saved subtitles.
    """
    filedata = json.dumps(subs, indent=2)
    mime_type = 'application/json'
    filename = 'subs_{0}.srt.sjson'.format(subs_id)

    content_location = StaticContent.compute_location(
        item.location.org, item.location.course, filename)
    content = StaticContent(content_location, filename, mime_type, filedata)
    contentstore().save(content)
    del_cached_content(content_location)
    return content_location


def get_transcripts_from_youtube(youtube_id):
    """
    Gets transcripts from youtube for youtube_id.

    Returns (status, transcripts): bool, dict.
    """
    html_parser = HTMLParser.HTMLParser()
    utf8_parser = etree.XMLParser(encoding='utf-8')
    settings.YOUTUBE_API['params']['v'] = youtube_id
    data = requests.get(
        settings.YOUTUBE_API['url'],
        params=settings.YOUTUBE_API['params']
    )
    if data.status_code != 200 or not data.text:
        log.debug("Can't receive correct transcripts from Youtube.")
        return False,  {}

    sub_starts, sub_ends, sub_texts = [], [], []
    xmltree = etree.fromstring(data.text.encode('utf-8'), parser=utf8_parser)
    for element in xmltree:
        if element.tag == "text":
            start = float(element.get("start"))
            duration = float(element.get("dur", 0))  # dur is not mandatory
            text = element.text
            end = start + duration

            if text:
                # Start and end should be ints representing the millisecond timestamp.
                sub_starts.append(int(start * 1000))
                sub_ends.append(int((end + 0.0001) * 1000))
                sub_texts.append(html_parser.unescape(text.replace('\n', ' ')))

    return True, {'start': sub_starts, 'end': sub_ends, 'text': sub_texts}


def download_youtube_subs(youtube_subs, item):
    """
    Download transcripts from Youtube and save them to assets.

    Args:
    youtube_subs: dict, speed: youtube_id.

    Returns: bool, True if transcripts were successfully downloaded and saved.
    """
    status_dict = {}
    # Iterate from lowest to highest speed and try to do download transcripts
    # from the Youtube service.
    for speed, youtube_id in sorted(youtube_subs.iteritems()):
        if not youtube_id:
            continue

        status, subs = get_transcripts_from_youtube(youtube_id)
        if not subs:  # if google return empty subs
            status = False
        if not status:
            status_dict.update({speed: status})
            continue

        available_speed = speed
        save_subs_to_store(subs, youtube_id, item)

        log.info(
            """transcripts for Youtube ID {0} (speed {1})
            are downloaded from Youtube and
            saved.""".format(youtube_id, speed)
        )

        status_dict.update({speed: True, 'subs': subs, 'available_speed': available_speed})

    if not any(status_dict.itervalues()):
        log.error("Can't find any transcripts on the Youtube service.")
        return False

    # When we exit from the previous loop, `available_speed` and `subs`
    # in status_dict are the transcripts data with the highest speed available on the
    # Youtube service. We use the highest speed as main speed for the
    # generation other transcripts, cause during calculation timestamps
    # for lower speeds we just use multiplication istead of division.
    subs = status_dict['subs']
    available_speed = status_dict['available_speed']
    # Generate transcripts for missed speeds.
    for speed, status in status_dict.iteritems():
        if not status:
            save_subs_to_store(
                generate_subs(speed, available_speed, subs),
                youtube_subs[speed],
                item)

            log.info(
                """transcripts for Youtube ID {0} (speed {1})
                are generated from Youtube ID {2} (speed {3}) and
                saved.""".format(
                youtube_subs[speed],
                speed,
                youtube_subs[available_speed],
                available_speed)
            )

    return True


def remove_subs_from_store(subs_id, item):
    """
    Remove from store, if transcripts content exists.
    """
    filename = 'subs_{0}.srt.sjson'.format(subs_id)
    content_location = StaticContent.compute_location(
        item.location.org, item.location.course, filename)
    try:
        content = contentstore().find(content_location)
        contentstore().delete(content.get_id())
        log.info("Removed subs {} from store".format(subs_id))
    except NotFoundError:
        pass


def generate_subs_from_source(speed_subs, subs_type, subs_filedata, item):
    """Generate transcripts from source files (like SubRip format, etc.)
    and save them to assets for `item` module.
    We expect, that speed of source subs equal to 1

    :param speed_subs: dictionary {speed: sub_id, ...}
    :param subs_type: type of source subs: "srt", ...
    :param subs_filedata: content of source subs.
    :param item: module object.
    :returns: True, if all subs are generated and saved successfully.
    """
    html_parser = HTMLParser.HTMLParser()

    if subs_type != 'srt':
        raise TranscriptsGenerationException("We support only SubRip (*.srt) transcripts format.")
    srt_subs_obj = SubRipFile.from_string(subs_filedata)
    if not srt_subs_obj:
        raise TranscriptsGenerationException("Something wrong with SubRip transcripts file during parsing.")

    sub_starts = []
    sub_ends = []
    sub_texts = []

    for sub in srt_subs_obj:
        sub_starts.append(sub.start.ordinal)
        sub_ends.append(sub.end.ordinal)
        sub_texts.append(html_parser.unescape(sub.text.replace('\n', ' ')))

    subs = {
        'start': sub_starts,
        'end': sub_ends,
        'text': sub_texts}

    for speed, subs_id in speed_subs.iteritems():
        save_subs_to_store(
            generate_subs(speed, 1, subs),
            subs_id,
            item)

    return subs


def generate_srt_from_sjson(sjson_subs, speed):
    """Generate transcripts with speed = 1.0 from sjson to SubRip (*.srt).

    :param sjson_subs: "sjson" subs.
    :param speed: speed of `sjson_subs`.
    :returns: "srt" subs.
    """

    output = ''

    equal_len = len(sjson_subs['start']) == len(sjson_subs['end']) == len(sjson_subs['text'])
    if not equal_len:
        return output

    sjson_speed_1 = generate_subs(speed, 1, sjson_subs)

    for i in range(len(sjson_speed_1['start'])):
        item = SubRipItem(
            index=i,
            start=SubRipTime(milliseconds=sjson_speed_1['start'][i]),
            end=SubRipTime(milliseconds=sjson_speed_1['end'][i]),
            text=sjson_speed_1['text'][i])
        output += (unicode(item))
        output += '\n'
    return output


def save_module(item):
    """
    Proceed with additional save operations.
    """
    item.save()
    store = get_modulestore(Location(item.id))
    store.update_metadata(item.id, own_metadata(item))
    return item


def copy_or_rename_transcript(new_name, old_name, item, delete_old=False):
    """
    Renames `old_name` transcript file in storage to `new_name`.

    If `old_name` is not found in storage, raises `NotFoundError`.
    If `delete_old` is True, removes `old_name` files from storage.
    """
    filename = 'subs_{0}.srt.sjson'.format(old_name)
    content_location = StaticContent.compute_location(
        item.location.org, item.location.course, filename)
    transcripts = contentstore().find(content_location).data
    save_subs_to_store(json.loads(transcripts), new_name, item)
    item.sub = new_name
    item = save_module(item)
    if delete_old:
        remove_subs_from_store(old_name, item)


def manage_video_subtitles_save(old_item, new_item):
    """
    Does some specific thins, that can be done only on save.

    Video player item has some video fields: HTML5 ones and Youtube one.

    1. If value of `sub` field of `new_item` is different from values of video fields of `new_item`,
    and `new_item.sub` file is present, then code in this function creates copies of
    `new_item.sub` file with new names. That names are equal to values of video fields of `new_item`
    After that `sub` field of `new_item` is changed to one of values of video fields.
    This whole action ensures that after user changes video fields, proper `sub` files, corresponding
    to new values of video fields, will be presented in system.

    old_item is not used here, but is added for future changes.
    """

    # 1.
    # assume '.' and '/' are not in filenames
    html5_ids = [x.split('/')[-1].split('.')[0] for x in new_item.html5_sources]
    possible_video_id_list = [new_item.youtube_id_1_0] + html5_ids
    sub_name = new_item.sub
    for video_id in [x for x in possible_video_id_list if x]:
        # copy_or_rename_transcript changes item.sub of module
        status = copy_or_rename_transcript(video_id, sub_name, new_item)
        log.debug("Copying {} file content to {} name is {}".format(sub_name, video_id, status))
