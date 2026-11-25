# qemu-ppc-screamer

QEMU 11.1.3 for PowerPC Macs (`mac99`, `g3beige`) with working Screamer (AWACS) onboard audio, as used by ZKM | Center for Art and Media Karlsruhe to run born-digital artworks on Mac OS 9 and Mac OS X 10.4.

Screamer is not part of upstream QEMU. The device is the work of Mark Cave-Ayland ([mcayland/qemu](https://github.com/mcayland/qemu), branch `screamer-v10.2.0` at `a3a5fd79`); patches 0001 to 0011 are the commits of that branch unchanged, without the commit that adds a prebuilt OpenBIOS. Rhizome published build notes for the earlier `screamer` branch in [rhizomedotorg/qemu-ppc-screamer](https://github.com/rhizomedotorg/qemu-ppc-screamer).

| Patch | Purpose |
|---|---|
| 0001–0011 | Screamer device by Mark Cave-Ayland |
| 0012 | port to QEMU 11.1 |
| 0013, 0014, 0016 | TCG speed |
| 0015 | keep playing across sample rate changes |
| 0017 | read guest audio at the sample rate: no more dropouts on Mac OS X, see [docs/audio-dropouts.md](docs/audio-dropouts.md) |
| 0018 | ignore DBDMA accesses beyond the channel registers |
| 0019 | codec readback index and register order |

`patches/openbios` adds the AWACS node to the OpenBIOS that QEMU ships (the commit `3d3c61d2` of [mcayland/openbios](https://github.com/mcayland/openbios), branch `screamer-v9.1.0`); OpenBIOS is rebuilt from source.

Patches 0012 to 0019 are maintained in this repository.

## Build

Needs Docker with BuildKit. The image only builds; the last stage holds nothing but the install prefix. The prefix `/opt/qemu-screamer-<version>` is compiled in.

```
V=$(cat VERSION)
docker build --build-arg IMAGE_VERSION=$V --output type=local,dest=/tmp/qemu-ppc-$V .
sudo cp -a /tmp/qemu-ppc-$V/opt/qemu-screamer-$V /opt/
```

The build uses 4 jobs, `--build-arg JOBS=8` changes that.

## Run

The binary is linked against Debian 13. Runtime packages on the host:

```
sudo apt install libglib2.0-0t64 libpixman-1-0 libslirp0 zlib1g libpng16-16t64 libfdt1 libpulse0 libpipewire-0.3-0t64 libsdl2-2.0-0
```

Then, with a disk image `disk.qcow2` that holds an installed Mac OS:

```
/opt/qemu-screamer-$(cat VERSION)/bin/qemu-system-ppc -M mac99,via=pmu -cpu g4 -m 1024 -boot c \
  -audiodev pa,id=audio1 -global screamer.audiodev=audio1 \
  -device VGA -vga none -prom-env 'vga-ndrv?=true' -drive file=disk.qcow2,format=qcow2
```

`-global screamer.audiodev=` is required: QEMU no longer falls back to the first audio device. The PipeWire backend (`-audiodev pipewire,id=audio1`) is compiled in too. Mac OS X keeps the hardware clock in UTC, which is the QEMU default (`-rtc base=utc`); for Mac OS 9, which expects local time, add `-rtc base=localtime`.

## Measure

`tools/gaps.py take.wav` counts dropouts in a 16 bit stereo recording. It needs numpy:

```
python3 -m venv venv
venv/bin/pip install numpy
venv/bin/python tools/gaps.py take.wav
```

## How the patches were written

Patches 0017 to 0019, the measurement and the documentation were written by AI agents, directed by one conservator at ZKM. QEMU [declines contributions with AI generated content](https://www.qemu.org/docs/master/devel/code-provenance.html), so please do not submit these patches upstream.

## License

QEMU as a whole is GPL-2.0, see [LICENSE](LICENSE); this repository is distributed under the same terms. The headers of the patched files apply; the files of the Screamer device carry Mark Cave-Ayland's copyright and a permissive (MIT) notice.

A ZKM open-source project, part of the [vmctl](https://github.com/zkmkarlsruhe/vmctl) family.
