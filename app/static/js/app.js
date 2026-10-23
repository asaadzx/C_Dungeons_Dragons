/* ===========================================================================
   app.js
   Shared progressive-enhancement script for the C! RAS Hub.

   NES.css needs no JavaScript at all, so this file only holds small UI
   helpers. It is loaded at the end of base.html.

   The DOMContentLoaded wrapper waits until the HTML is fully parsed before
   running, which is the safe place to attach event listeners.
   =========================================================================== */

document.addEventListener("DOMContentLoaded", function () {
  // -------------------------------------------------------------------------
  // Navigation dropdown
  // The three main links stay visible; the "Menu" button reveals the rest.
  // -------------------------------------------------------------------------
  var toggle = document.getElementById("menu-toggle");
  var menu = document.getElementById("nav-more");

  if (toggle && menu) {
    var closeMenu = function () {
      menu.hidden = true;
      toggle.setAttribute("aria-expanded", "false");
    };

    toggle.addEventListener("click", function (event) {
      // Stop the click from reaching the document handler below, otherwise
      // it would immediately close the menu again.
      event.stopPropagation();
      var willOpen = menu.hidden;
      menu.hidden = !willOpen;
      toggle.setAttribute("aria-expanded", String(willOpen));
    });

    // Close when clicking anywhere outside the menu.
    document.addEventListener("click", function (event) {
      if (!menu.hidden && !menu.contains(event.target) && event.target !== toggle) {
        closeMenu();
      }
    });

    // Close with the Escape key.
    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape") {
        closeMenu();
      }
    });
  }

  // Log a friendly message so it is obvious the script loaded correctly.
  console.log("C! RAS Hub ready.");
});
