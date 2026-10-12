# D-03-DEVICE-IMAGE: open questions (DEVIMG-PLAN, 2026-10-11)

Efforts are from claude/timings.md (agent fix / feature: 3-8 min per agent,
inside the batch already quoted in split.md unless said otherwise).

1. The Export / Import Device window's "Device photo" row. Today the pack
   import list has a separate row and tick for the bottom background picture
   ("Device photo", device_pack.py `_zip_pictures` 1214-1251,
   `_merge_background` 1564-1602), because that layer WAS the device's
   uploaded photo. With the image as its own file, that row means only "the
   bottom background layer". (08 S75 changes either way.)

   a) Recommended: the "Device photo" row goes; the bottom background
      picture travels with the background like any other background picture
      (the Map tick), and a new "Device image" row carries the image. Cleanest
      design: one row per thing the user sees. Effort: +3-8 min inside A-PACK
      and T-SWEEP (timings.md: agent fix); 3 existing tests in
      test_planes_carry.py change.

   b) Keep the row, renamed "Bottom background picture", beside the new
      "Device image" row. Effort: about 1 min more (wording only).

2. Copy Setup to Another Stick and Swap with Another Stick: does the device
   image move? (library_copy.py `_PART_ITEMS` 39-44; library_swap.py
   `_MAP_KEYS` 30.)

   a) Recommended: no; each stick keeps its own image (it is a picture of
      that stick's hardware; copying a VKB setup onto a Thrustmaster must not
      put the VKB's picture on the Thrustmaster card). Device Library Restore
      onto the same stick and Import Device do take it. Effort: none beyond
      the batch (no code in Copy / Swap; T-CARRY proves it).

   b) It goes with the Setup part (copied and swapped with claims and
      names). Effort: +3-8 min in A-PACK (library_copy) and library_swap.py
      (one more owner).

3. Import onto an existing device: the new "Device image" row's default.

   a) Recommended: ticked, like the other rows; the red Replace warning
      (08 S64) lists it, so nothing is replaced unseen. Effort: none extra.

   b) Unticked when this device already has its own image. Effort: +3-8 min
      in A-PACK.

4. Output cards. You said "every INPUT card and the Logical Device". Module
   Setup also opens for vJoy output devices, and its Import Image becomes
   Add / Change / Remove there too (one Module Setup window), so vJoy
   outputs can get an image anyway. HidHide's vJoy rows (label "vJoy N",
   hidhide.py:480-483) would also set it.

   a) Recommended: the card menu items on vJoy output cards too, so every
      device that can have an image has the same three items; not on the
      Xbox card (it has no Module Setup, 03 S88, and the Xbox output module
      is a pass-through with no claims; whether it has its own device folder
      is NOT VERIFIED). Effort: none extra (one condition in StatusCard.qml).

   b) Inputs and Logical Device only on the card menu, as said; vJoy only
      through Module Setup / HidHide. Effort: none.

5. HidHide rows that are linked to no device (`module` "" in
   `_enrich_devices`, hidhide.py:576-606: no VID/PID match, not a vJoy
   collection). One image per device means there is no device to put it on.

   a) Recommended: the Add Image button is disabled on such a row, with the
      tooltip "Not linked to a device". The per-row picture setting
      (`display/hidhide/photos`) goes entirely. Effort: none extra.

   b) Keep the old per-row picked picture only for unlinked rows (02 S82 as
      today for them). Effort: +3-8 min; two picture rules in one window.

6. HidHide Remove Image. Your decision names Add / Change there only.

   a) Recommended: no Remove button in HidHide; Remove Image is on the Home
      card menu and in Module Setup. Keeps the row narrow. Effort: none.

   b) Add a Remove Image button to the row. Effort: +3-8 min in A-HIDHIDE.

7. The bottom background picture fallback while the generated picture is
   being made (you asked whether it still makes sense).

   a) Recommended: keep it as the third choice. It is what shows during the
      second the maker takes after a save, when the maker has no window to
      draw in (`DevicePhotoMaker.hostReady` false: tests, before the main
      window loads), and for an old pack without device-photo.png. Without
      it those cases show no picture. Already built; effort: none.

   b) Drop it: image, else the generated picture, else nothing. Effort:
      3-8 min (store.shown_photo_ref and 4 tests in test_device_photo_shown.py).

8. Old maps' top-level "image" key (one-time code OT-2,
   `planes_once.old_photo_to_layer`, still called on load, swap and pack
   import). Today it turns that old photo into the bottom background layer.

   a) Recommended: leave OT-2 as it is (it reads layouts from before the
      planes and is due for removal; the program is unreleased). Effort: none.

   b) Make the old "image" the device image instead. Effort: +3-8 min, and
      it changes one-time code that is meant to go (tracker OT-2 update).

9. Pictures uploaded before this change (bottom background layers named
   `photo.<ext>`) and HidHide pictures picked before.

   a) Recommended: no move (unreleased program, CLAUDE.md "no legacy
      compatibility by default"). What you will see: cards look the same
      (the generated background picture includes the old upload); the menu
      offers Add Image… because there is no device image yet; the old upload
      is removed in the Device Mapping Editor's Background, not by Remove
      Image; HidHide rows you gave a picture show the device's photo
      instead. Effort: none.

   b) A one-time move: turn each device's bottom `photo.*` layer into its
      device image and each HidHide picked picture into the linked device's
      image. Effort: +3-8 min plus tracking as one-time code (tracker issue,
      ONE-TIME comment, todo line).
