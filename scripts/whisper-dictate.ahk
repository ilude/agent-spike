; WhisperWriter Mouse Button Trigger
; Maps the forward mouse button (XButton2) to F13 for WhisperWriter activation
;
; Installation:
;   1. Install AutoHotkey v2: https://www.autohotkey.com/
;   2. Double-click this script to run
;   3. (Optional) Add to Windows Startup folder for auto-start
;
; Alternative: Use Logitech Options+ to map the forward button directly to F13

#Requires AutoHotkey v2.0

; Forward mouse button (furthest forward on M720) sends F13
; WhisperWriter should be configured with activation_key: f13
XButton2::Send "{F13}"

; Optional: Back button for a different function (uncomment if needed)
; XButton1::Send "{F14}"
