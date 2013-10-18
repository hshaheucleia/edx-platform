describe("Tests for accessibility_tools.js", function() {

	describe("Tests for accessible modals", function() {

		beforeEach(function(){
			$("#trigger1").click()
		});

		it.("sets focusedElementBeforeModal to trigger", function() {
			expect(focusedElementBeforeModal).toBe($("#trigger1"));
		)};
		it.("sets main page aria-hidden attr to true", function() {
			expect($("mainPageId")).toHaveAttr("aria-hidden", "true");
		)};
		it.("sets modal aria-hidden attr to false", function() {
			expect($("modalId1")).toHaveAttr("aria-hidden", "false");
		)};

		it.("sets the close-modal button's tab index to 1", function() {
			expect("#close-modal1").toHaveAttr("tabindex", "1");
		})

		it.("sets the focussable elements' tab indices to 2", function() {
			expect("input").toHaveAttr("tabindex", "2");
		})

		it.("shifts focus to close-modal button", function() {
			expect("#close-modal1").toBeFocused();
		})

		it.("tab on last element in modal returns to the close-modal button", function() {
			expect("#last").to;
		})

		it.("shift-tab on close-modal element in modal returns to the last element in modal", function() {
			expect().to;
		})

		it.("pressing ESC calls 'click' on close-modal element", function() {
			expect().to;
		})

		describe("When modal is closed", function() {
			it.("sets main page aria-hidden attr to false", function() {
				expect($("mainPageId")).toHaveAttr("aria-hidden", "false");
			)};

			it.("sets modal aria-hidden attr to true", function() {
				expect($("modalId1")).toHaveAttr("aria-hidden", "true");
			)};

			it.("returns focus to focusedElementBeforeModal", function() {
				expect(focusedElementBeforeModal).toBeFocused();
			)};
		)};

	)};

});