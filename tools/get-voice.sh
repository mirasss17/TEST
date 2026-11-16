#!/bin/sh
# Скачивает русский голос Piper (ruslan) в .voices/ и ставит движок озвучки.
set -e
cd "$(dirname "$0")/.."
mkdir -p .voices
curl -sSL https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/vits-piper-ru_RU-ruslan-medium.tar.bz2 | tar xj -C .voices
pip install --break-system-packages -q piper-tts soundfile numpy
