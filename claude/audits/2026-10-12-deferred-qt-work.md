# Deferred Qt work left by tests (to-do 133), 2026-10-12, agent Q133 (read-only)

Method: scratch pytest plugin (scratchpad/q133/leakwatch.py) counting pending DeferredDelete (event filter during an explicit flush), Python QObjects still alive, and receiver growth on gremlin.signal / EventListener / EventHandler, over the 35 files before the crashed parts + test_stage1_app_profile, in one process, with and without a flush. 413 passed both times; the crash is intermittent.

Verified:
1. test/unit/test_final_06.py leaves 4 deleteLater objects (MapToKeyboardModel, _Binding at lines 456-457; LogicalLayoutModel per `assign` fixture use at 618). They stay pending until a later test runs an exec loop; without a flush they were deleted inside test_owner_notices_senders' qtbot.wait — same part and stack as crash 797969 (_settle -> qtbot.wait -> exec).
2. test_sendosc_target_name.py leaves RootModel, SendOscModel, InputItemBindingModel, VirtualButtonModel alive; +1 receiver per test on inputItemChanged, oscServerSettingsChanged, cantSendChanged.
3. Connections without a live object (lambdas/closures, unverified): test_osc_encoder (oscDeviceReloaded, oscServerSettingsChanged), test_device_photo_maker (configChanged).
Not leaks: one-time shared objects (InputModuleRuntime, _CantSendNotice, ModeManager, OscRuntime, NoticeTimer).
Unexplained: crashes 20892 and 789502 died in processEvents() (no deleteLater there): likely queued calls/timers reaching leftovers (unverified).

Proposed (next batch, needs a full run): autouse root fixture flushing DeferredDelete at each test's end (tested on test_final_06); optional per-test receiver-growth check naming the leaking test; fix test_final_06 and test_sendosc_target_name at the source.
