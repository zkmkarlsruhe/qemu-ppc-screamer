# Screamer audio on Mac OS X guests: cause and fix (11.1.3-zkm5)

Covers patches 0017 to 0019 of this repository. `zkm5` is the build with all patches, `zkm4` the build before them. The device itself comes from Mark Cave-Ayland's `screamer` branch; patches 0001 to 0011 carry the author's work.

## Symptom
Mac OS X 10.4.11 on `mac99,via=pmu` (TCG) dropped audio. In 118 s of a sound program we counted 898 gaps, 24.8 % of the audible time. A 441 Hz test tone played by QuickTime Player showed the fault as well, so the sound program is not the cause.

## Cause
1. The Mac OS X driver uses a ring of 16384 frames. Only the last descriptor raises an interrupt.
2. Between two interrupts CoreAudio predicts the hardware position and writes just ahead of it, with a safety margin of 45 frames.
3. The emulated device filled its host buffer (2049 frames) from guest memory in one burst. The read ran far past the margin, into memory CoreAudio had not written yet. The host played zeros.

A real Screamer reads at the sample rate, so the margin is enough there.

## Evidence
The ends of the gaps lie on a grid that equals the burst size. We changed the burst size and nothing else (the test builds A, B and C are not part of this repository):

| Build | Burst (frames) | Grid of gap ends | Gaps in 118 s | Loss of audible time |
|---|---|---|---|---|
| zkm4 | 2049 | 2049 | 898 | 24.8 % |
| test A | 1024 | 1024.0 | 124 | 1.5 % |
| test B | 941 | 940.75 | 124 | 0.7 % |
| test C | at most 48 | – | 8 and 12 (two runs) | 0.3 to 0.4 % |
| zkm5 | paced | – | 0 | 0 % |

Tested and excluded: guest RAM (896 MB instead of 1024 MB), audio timer period 2000, the sound program.

## Fix
- **0017, pacing.** A timer on the virtual clock reads the TX channel at the sample rate, at most 1 ms per step. Samples go to a FIFO on the host side, with 20 ms prebuffer. Descriptor completion, interrupts and the frame counter share one timeline. After a stall the device catches up at no more than twice virtual time. A trim of at most 0.5 % follows the host clock. New qtest: `tests/qtest/screamer-test.c`.
- **0018, DBDMA.** Register offsets beyond the 16 channel registers are ignored and logged. QEMU master also limits the access to the implemented registers (commit 6c16381150).
- **0019, codec.** The readback index was shifted after masking; it now stays inside the eight registers and the value sits in bits 4 to 15. A codec register is stored before mute and attenuation are applied.

## Results with zkm5
- The same program: 0 gaps in 118 s; one gap of 13.2 ms in 20 minutes.
- 441 Hz tone, 38 s: 0 phase steps (zkm4: 359).
- Our acceptance test on Mac OS X 10.4 and Mac OS 9 passes.

## Limits
- Only Mac OS X 10.4.11 is measured for this fault. Mac OS 9 passes our acceptance test; its sound was not compared before and after.
- From Apple's published driver sources we expect the same fault on 10.1 to 10.3 and 10.5. Not measured.
- The device cannot be migrated while this patch is in place (`unmigratable`).
- A local SDL window costs audio, see below. Use `-display none -vnc 127.0.0.1:77` and a separate viewer (`remote-viewer --kiosk --full-screen vnc://127.0.0.1:5977`).
- Input (recording) is not implemented.

## SDL window
Same program, 10 minutes each, loaded host (load 8 to 9), software rendered X display:

| Display | Gaps |
|---|---|
| SDL, fullscreen / window / software renderer / without vsync | 26 / 36 / 60 / 32 |
| SDL fullscreen with call timing | 33 |
| SDL, window presented once per refresh (test D, two runs) | 3 and 10 |
| as D, and the BQL dropped while presenting (test E, two runs) | 1 and 1 |
| no display | 0 |
| VNC without / with a viewer (TigerVNC, remote-viewer) | 0 / 0 and 0 |

QEMU presents the window in the main loop with the BQL held. In the timed run 94 % of the gaps had an `SDL_RenderPresent` of more than 3 ms close by; with a random time offset it was 21 %. The offset was fitted. Test D cut the number of presentations by about 4 % only, so why it helps is open. The test patches are not in the build: dropping the BQL while presenting is not safe for display devices that update the surface from another thread.

## Reproducing the measurement
Record the host sink for 120 s. `tools/gaps.py` counts runs of exact zeros of 1 to 350 ms with signal above -50 dBFS in the 5 ms on both sides. It divides the gap time by the audible time plus gap time. For the cause: take the position of each gap end modulo a candidate burst size and compute the circular mean length; random positions give at most 0.19.
