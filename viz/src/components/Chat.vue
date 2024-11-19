<script setup lang="ts">
import ChatMessages from "@/components/ChatMessages.vue";
import type { InteractiveClient } from "@/pal/interactive-openai";
import type { ReDelState } from "@/redel/state";
import autosize from "autosize";
import WaveSurfer from "wavesurfer.js";
import RecordPlugin from "wavesurfer.js/dist/plugins/record.esm.js";
import { inject, nextTick, onBeforeUnmount, onMounted, ref, shallowRef } from "vue";
import { RunState } from "@/redel/models";

const client = inject<InteractiveClient>("client")!;
const state = inject<ReDelState>("state")!;

const chatInput = ref<HTMLInputElement | null>(null);
const chatMsg = ref("");
const chatMessages = ref<InstanceType<typeof ChatMessages> | null>(null);
const waveSurfer = shallowRef<WaveSurfer | null>(null);
const waveformRef = ref<HTMLDivElement | null>(null);
const controllerContainer = ref<HTMLDivElement | null>(null);
const paused = ref(true);
const global_pause_count = ref(0);
const progress = ref("00:00");
const isSpeechEnabled = ref(true);
const isEnded = ref(false);
let record: any = null;

// audio capture toggle
let push_to_talk = true;

const inputAudioBuffer = shallowRef<Int16Array[] | null>(null);
const inputAudioContext = shallowRef<AudioContext | null>(null);
const source = shallowRef<MediaStreamAudioSourceNode | null>(null);
const processor = shallowRef<ScriptProcessorNode | null>(null);

function toggleSpeech() {
  isSpeechEnabled.value = !isSpeechEnabled.value;
}
function end() {
  isEnded.value = true;
}

async function sendChatMsg() {
  const msg = chatMsg.value.trim();
  if (msg.length === 0) return;
  chatMsg.value = "";
  nextTick(() => autosize.update(chatInput.value!));
  client.sendMessage(msg);
  chatMessages.value?.scrollChatToBottom();
  // wait for reply
  await client.waitForFullReply();
  setTimeout(() => {
    chatInput.value?.focus();
  }, 0);
}

async function startRealtimeListening() {
  if (push_to_talk) return;

  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        sampleRate: 24000,
        channelCount: 1,
        echoCancellation: true,
      },
    });

    inputAudioBuffer.value = [];
    inputAudioContext.value = new AudioContext({ sampleRate: 24000 });
    source.value = inputAudioContext.value.createMediaStreamSource(stream);
    processor.value = inputAudioContext.value.createScriptProcessor(4096, 1, 1);

    processor.value.onaudioprocess = (event) => {
      const audioData = event.inputBuffer.getChannelData(0);

      const int16Buffer = new Int16Array(convertFloat32ToInt16(audioData));
      inputAudioBuffer.value?.push(int16Buffer);

      client.appendAudio(int16Buffer);
    };

    source.value.connect(processor.value);
    processor.value.connect(inputAudioContext.value.destination);
  } catch (error) {
    console.error(error);
  }
}

async function toggleAudioCapture() {
  if (paused.value && source.value && processor.value && inputAudioContext.value) {
    source.value.connect(processor.value);
    processor.value.connect(inputAudioContext.value.destination);
  } else if (!paused.value) {
    source.value?.disconnect();
    processor.value?.disconnect();
  }
}

const createWaveSurfer = () => {
  if (waveSurfer.value) {
    waveSurfer.value.destroy();
  }

  waveSurfer.value = WaveSurfer.create({
    container: waveformRef.value!,
    height: 50,
    waveColor: "rgb(200, 0, 200)",
    progressColor: "rgb(100, 0, 100)",
    barWidth: 2,
    barGap: 1,
    barRadius: 2,
    cursorColor: "transparent",
    backend: "WebAudio",
  });

  record = waveSurfer.value.registerPlugin(
    RecordPlugin.create({
      scrollingWaveform: true,
      renderRecordedAudio: false,
    }),
  );

  record.on("record-progress", (time: number) => {
    updateProgress(time);
  });

  if (push_to_talk) {
    record.on("record-data-available", (blob: Blob) => {
      recordDataAvailable(blob);
    });
  }
};

async function toggleMicrophone() {
  if (record.isRecording() || record.isPaused()) {
    toggleAudioCapture();
    paused.value = !record.isPaused();

    if (record.isPaused()) {
      record.resumeRecording();
      global_pause_count.value += 1;
    } else {
      if (push_to_talk) {
        record.stopRecording();
        global_pause_count.value = 0;
      } else {
        record.pauseRecording();
      }
    }
  } else {
    paused.value = false;
    await record.startRecording({});
    global_pause_count.value += 1;

    startRealtimeListening();
  }
}

onMounted(() => {
  autosize(chatInput.value!);

  createWaveSurfer();
  RecordPlugin.getAvailableAudioDevices().then((devices: any[]) => {
    devices.forEach((device: { deviceId: string; label: any }) => {
      const option = document.createElement("option");
      option.value = device.deviceId;
      option.text = device.label || device.deviceId;
    });
  });
});

onBeforeUnmount(() => {
  if (waveSurfer.value) {
    waveSurfer.value.destroy();
  }
});

const updateProgress = (time: number) => {
  const minutes = Math.floor((time % 3600000) / 60000);
  const seconds = Math.floor((time % 60000) / 1000);
  progress.value = `${minutes < 10 ? "0" : ""}${minutes}:${seconds < 10 ? "0" : ""}${seconds}`;
};

async function recordDataAvailable(blob: Blob) {
  const audioBuffer = await blob.arrayBuffer();
  const audioContext = new AudioContext({ sampleRate: 24000 });
  audioContext.decodeAudioData(
    audioBuffer,
    (decodedData) => {
      const sampleRate = audioContext.sampleRate;
      const numChannels = decodedData.numberOfChannels;
      const length = decodedData.length * numChannels;
      const audio = new Int16Array(length);
      for (let i = 0; i < decodedData.length; i++) {
        for (let channel = 0; channel < numChannels; channel++) {
          const sample = decodedData.getChannelData(channel)[i];
          audio[i * numChannels + channel] = Math.max(-1, Math.min(1, sample)) * 32767; // Convert to 16-bit PCM
        }
      }
      client.appendAudio(audio);
    },
    (error) => {
      console.error("Error decoding audio data:", error);
    },
  );
}

function convertFloat32ToInt16(buffer: any) {
  let l = buffer.length;
  const buf = new Int16Array(l);
  while (l--) {
    buf[l] = Math.min(1, buffer[l]) * 0x7fff;
  }
  return buf.buffer;
}

defineExpose({ toggleSpeech, end, isEnded });
</script>

<template>
  <div class="is-flex is-flex-direction-column h-100">
    <div class="is-flex-grow-1"></div>
    <!-- chat history -->
    <ChatMessages :kani="state.rootKani!" v-if="state.rootKani" ref="chatMessages" />
    <!-- msg bar -->
    <div class="chat-box" v-show="!isEnded">
      <div class="controller-container" :class="{ paused: global_pause_count == 0 }" ref="controllerContainer">
        <p class="paused-expand">{{ progress }}</p>
        <div id="waveform" ref="waveformRef" class="waveform-container paused-expand"></div>
        <button @click="toggleMicrophone" class="start-interview has-fixed-size" v-show="isSpeechEnabled">
          <span class="icon is-small mt-1">
            <font-awesome-icon :icon="['fas', 'play']" class="fa-xs" v-show="paused" />
            <font-awesome-icon :icon="['fas', 'pause']" class="fa-xs" v-show="!paused" />
          </span>
        </button>
        <textarea
        class="textarea has-fixed-size"
        :disabled="state.rootKani?.state !== RunState.stopped"
        autofocus
        rows="1"
        ref="chatInput"
        v-model.trim="chatMsg"
        v-show="!isSpeechEnabled"
        @keydown.enter.exact.prevent="sendChatMsg"
      ></textarea>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
@import "@/global.scss";

.controller-container {
  background: rgba($beige-light, 0.4);
  padding: 2rem 4rem 2rem 4rem;

  text-align: center;
}

#waveform {
  margin-top: 1rem;
  margin-bottom: 1.5rem;
}

.paused .paused-expand {
  display: none;
}

.start-interview {
  display: block;
  background: rgba($purple, 1);
  width: 3rem;
  height: 3rem;
  margin: auto;
  border: rgba(white, 0.5) 2px solid;
  border-radius: 100%;
  padding: 0.5rem;

  color: white;
  font-weight: bold;
  font-size: 1.5rem;

  &:hover {
    background: rgba($purple, 0.8);
  }
}

svg.fa-play {
  margin-left: 3px;
}

svg.fa-xs {
  height: 100%;
}
</style>
