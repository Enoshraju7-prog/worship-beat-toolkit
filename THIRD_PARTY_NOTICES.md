# Code, models and media have different rights

The MIT license in this repository covers original toolkit code and documentation. Dependencies, external tools, model checkpoints, music, performances and lyrics retain their respective rights. Processing a recording does not grant permission to distribute it or its stems.

No song audio, stock sample pack, model checkpoint, cookie file, credential or virtual environment is shipped in this repository. Generated software fixtures are explicitly labeled and do not represent any song.

## Separation

[Demucs](https://github.com/facebookresearch/demucs) provides the separation architecture and official checkpoints. Its upstream source repository includes its license and model information. Consult those terms for the version/model you use; this repository's MIT license does not relicense weights. Torch checkpoints are downloaded from the upstream `dl.fbaipublicfiles.com/demucs/hybrid_transformer/` location and checked against full SHA-256 digests before loading.

| Toolkit mode | htdemucs_ft specialist | Filename | SHA-256 |
| --- | --- | --- | --- |
| Drums | Drum-specialist model | `f7e0c4bc-ba3fe64a.th` | `ba3fe64ae8ef66ac9a4857222ce48efbdc5eb3ad375cb79dd13debee5aaa4066` |
| Accompaniment | Vocal-specialist model, then subtract estimated vocals | `04573f0d-f3cf25b2.th` | `f3cf25b222c4eed7cd49dd8b2c9597d50c18bd154090f7b919cfa5f93cf22c49` |

Loading the verified legacy checkpoint uses Python/PyTorch serialization. The loader's compatibility setting is scoped to this operation; do not adapt it to accept arbitrary unverified checkpoint files.

## Runtime dependencies

| Component | Role | Upstream |
| --- | --- | --- |
| FFmpeg | Decode and time-stretch | [FFmpeg legal information](https://ffmpeg.org/legal.html); obligations depend on the installed build |
| yt-dlp | Optional source download | [yt-dlp licensing](https://github.com/yt-dlp/yt-dlp#license) |
| PyTorch / torchaudio | Local model runtime | [PyTorch](https://github.com/pytorch/pytorch), [torchaudio](https://github.com/pytorch/audio) |
| NumPy / SciPy | Signal and array operations | [NumPy](https://numpy.org/), [SciPy](https://scipy.org/) |
| librosa | Spectral features | [librosa](https://github.com/librosa/librosa) |
| SoundFile / libsndfile | PCM read/write | [SoundFile](https://github.com/bastibe/python-soundfile) |
| soxr / libsoxr | Resampling | [python-soxr](https://github.com/dofuuz/python-soxr) |
| Streamlit / pandas | Local review app | [Streamlit](https://github.com/streamlit/streamlit), [pandas](https://github.com/pandas-dev/pandas) |

Each dependency is installed separately with its own license metadata. Transitive dependencies have their own notices too. Consult installed package metadata for exact versions. The pinned Apple Silicon constraints record the tested versions; they do not bundle the dependencies.

## Remixlive

Remixlive is a Mixvibes product and trademark. This is an independent toolkit, not an official Mixvibes integration. The adapter writes a minimal JSON/ZIP structure based on observation of an empty Remixlive 8.7.0 export; it includes an empty Song asset and generated metadata, with no proprietary stock audio/template. Compatibility must be checked in the actual app version and on the intended device.
