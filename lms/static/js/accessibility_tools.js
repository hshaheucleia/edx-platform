var focusedElementBeforeModal;

var accessible_modal = function(trigger, closeButtonId, modalId, mainPageId) {
  // Modifies a lean modal to optimize focus management.
  // "trigger" is the selector for the link element that triggers the modal.
  // "closeButtonId" is the selector for the button that closes out the modal.
  // "modalId" is the selector for the modal being managed
  // "mainPageId" is the selector for the main part of the page
  // 
  // see http://accessibility.oit.ncsu.edu/blog/2013/09/13/the-incredible-accessible-modal-dialog/
  // for more information on managing modals
  // 
  var focusableElementsString = "a[href], area[href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), button:not([disabled]), iframe, object, embed, *[tabindex], *[contenteditable]";

  $(trigger).click(function(){
    focusedElementBeforeModal = $(":focus");
    // when modal is opened, adjust tabindexes and aria-hidden attributes

    $(mainPageId).attr("aria-hidden", "true");
    $(modalId).attr("aria-hidden", "false");
  
    var focusableItems = $(modalId).find("*").filter(focusableElementsString).filter(':visible');
    
    focusableItems.attr("tabindex", "2");
    $(closeButtonId).attr("tabindex", "1");
    $(closeButtonId).focus()

    // define the last tabbable element to complete tab cycle
    var last;
    if (focusableItems.length !== 0) {
      last = focusableItems.last();
    } else {
      last = $(closeButtonId);
    };

    // tab on last element in modal returns to the first one
    last.on('keydown', function(e) {
      var keyCode = e.keyCode || e.which;
      // 9 is the js keycode for tab
      if (!e.shiftKey && keyCode === 9) {
        e.preventDefault();
        $(closeButtonId).focus();
      }
    });

    // shift+tab on first element in modal returns to the last one
    $(closeButtonId).on('keydown', function(e) {
      var keyCode = e.keyCode || e.which;
      // 9 is the js keycode for tab
      if (e.shiftKey && keyCode == 9) {
        e.preventDefault();
        last.focus();
      }
    });

    // manage aria-hidden attrs, return focus to trigger on close
    $(closeButtonId).click(function(){
      $(mainPageId).attr("aria-hidden", "false");
      $(modalId).attr("aria-hidden", "true");
      focusedElementBeforeModal.focus()
    });

    // get modal to exit on escape key
    $(".modal").on("keydown", function(e) {
      var keyCode = e.keyCode || e.which;
      // 27 is the javascript keycode for the ESC key
      if (keyCode === 27) {
          e.preventDefault();
          $(closeButtonId).click();
      }
    });
  });
};
