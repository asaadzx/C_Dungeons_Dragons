/* ===========================================================================
   app.js
   Shared progressive-enhancement script for the C! RAS Hub.

   NES.css needs no JavaScript at all, so this file is intentionally tiny.
   It is loaded by base.html and left in place as a hook for future
   interactive features (e.g. team sign-up in a later milestone).

   The DOMContentLoaded wrapper waits until the HTML is fully parsed before
   running, which is the safe place to attach event listeners.
   =========================================================================== */

document.addEventListener("DOMContentLoaded", function () {
  // Log a friendly message so it is obvious the script loaded correctly.
  console.log("C! RAS Hub ready.");
});
