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
- A local SDL window costs audio: on one loaded host we counted 26 gaps of 12 to 14 ms in 10 minutes in fullscreen, 36 in a window, 60 with the software renderer and 32 without vsync. Without a display there were 0, and with `-display none -vnc` there were 0 with and without a connected viewer. One run each. Which part of the SDL path causes it is open.
- Input (recording) is not implemented.

## Reproducing the measurement
Record the host sink for 120 s. `tools/gaps.py` counts runs of exact zeros of 1 to 350 ms with signal above -50 dBFS in the 5 ms on both sides. It divides the gap time by the audible time plus gap time. For the cause: take the position of each gap end modulo a candidate burst size and compute the circular mean length; random positions give at most 0.19.
