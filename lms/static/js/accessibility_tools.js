var accessible_modal = function(trigger, close_button, tabbables, modal_id) {
  // Modifies a lean modal to optimize focus management.
  // "tabbables" are the jQuery selectors of the modal elements that you
  // what to tab through. The selector for the submit should go last.
  // The order of selectors determines their tabbing order
  // "close_button" is the selector for the button that closes out the modal.
  // "trigger" is the selector for the link element that triggers the modal.

  $(trigger).click(function(){
    // when modal is opened, adjust tabindexes
    $(close_button).attr("tabindex", "1");
    $(tabbables).attr("tabindex", "2");
    $(close_button).focus()

    // define the last tabbable element to complete tab cycle
    var last;
    if ($(tabbables).length !== 0) {
      last = $(tabbables).last();
    } else {
      last = $(close_button);
    };

    // tab on last element in modal returns to the first one
    last.on('keydown', function(e) {
      var keyCode = e.keyCode || e.which;
      // 9 is the js keycode for tab
      if (!e.shiftKey && keyCode === 9) {
        e.preventDefault();
        $(close_button).focus();
      }
    });

    // shift+tab on first element in modal returns to the last one
    $(close_button).on('keydown', function(e) {
      var keyCode = e.keyCode || e.which;
      // 9 is the js keycode for tab
      if (e.shiftKey && keyCode == 9) {
        e.preventDefault();
        last.focus();
      }
    });

    // return focus to trigger on close
    $(close_button).click(function(){
      $(trigger).focus()
    });

    // get modal to exit on escape key
    $(".modal").on("keydown", function(e) {
      var keyCode = e.keyCode || e.which;
      // 27 is the javascript keycode for the ESC key
      if (keyCode === 27) {
          e.preventDefault();
          $(close_button).click();
      }
    });
  });
};
