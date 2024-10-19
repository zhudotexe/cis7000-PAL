<script setup lang="ts">
import ChatMessages from "@/components/ChatMessages.vue";
import type { InteractiveClient } from "@/redel/interactive";
import { RunState } from "@/redel/models";
import type { ReDelState } from "@/redel/state";
import autosize from "autosize";
import WaveSurfer from "wavesurfer.js";
import RecordPlugin from 'wavesurfer.js/dist/plugins/record.esm.js';
import { inject, nextTick, onMounted, onBeforeUnmount, ref, shallowRef } from "vue";

const client = inject<InteractiveClient>("client")!;
const state = inject<ReDelState>("state")!;

const chatInput = ref<HTMLInputElement | null>(null);
const chatMsg = ref("");
const chatMessages = ref<InstanceType<typeof ChatMessages> | null>(null);
const waveSurfer = shallowRef<WaveSurfer | null>(null);
const waveformRef = ref<HTMLDivElement | null>(null);
const controllerContainer = ref<HTMLDivElement | null>(null);
const scrollingWaveform = ref(false);
const paused = ref(true);
const progress = ref("00:00");
let record: any = null;

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

const createWaveSurfer = () => {
  if (waveSurfer.value) {
    waveSurfer.value.destroy();
  }

  waveSurfer.value = WaveSurfer.create({
    container: waveformRef.value!,
    height: 50,
    waveColor: 'rgb(200, 0, 200)',
    progressColor: 'rgb(100, 0, 100)',
    barWidth: 2,
    barGap: 1,
    barRadius: 2,
    cursorColor: 'transparent'
  });

  record = waveSurfer.value.registerPlugin(RecordPlugin.create({
    scrollingWaveform: scrollingWaveform.value,
    renderRecordedAudio: false,
  }));

  record.on('record-progress', (time: number) => {
    updateProgress(time);
  });
};

const updateProgress = (time: number) => {
  const minutes = Math.floor((time % 3600000) / 60000);
  const seconds = Math.floor((time % 60000) / 1000);
  progress.value = `${minutes < 10 ? '0' : ''}${minutes}:${seconds < 10 ? '0' : ''}${seconds}`;
};

async function toggleMicrophone() {
  if (record.isRecording() || record.isPaused()) {
    paused.value = !record.isPaused();
    if (record.isPaused()) {
      record.resumeRecording();
    } else {
      record.pauseRecording();
    }
  } else {
    paused.value = false;
    await record.startRecording({});
  }
}

onMounted(() => {
  autosize(chatInput.value!);

  createWaveSurfer();
  RecordPlugin.getAvailableAudioDevices().then((devices) => {
    devices.forEach((device) => {
      const option = document.createElement('option');
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
</script>

<template>
  <div class="is-flex is-flex-direction-column h-100">
    <div class="is-flex-grow-1"></div>
    <!-- chat history -->
    <ChatMessages :kani="state.rootKani!" v-if="state.rootKani" ref="chatMessages" />
    <!-- msg bar -->
    <div class="chat-box">
      <div class="controller-container" :class="{ 'paused': paused }" ref="controllerContainer">
        <p class="paused-expand">{{ progress }}</p>
        <div id="waveform" ref="waveformRef" class="waveform-container paused-expand"></div>
        <button @click="toggleMicrophone" class="start-interview has-fixed-size">
          <span class="icon is-small mt-1">
            <font-awesome-icon :icon="['fas', 'play']" class="fa-xs" v-show="paused"/>
            <font-awesome-icon :icon="['fas', 'pause']" class="fa-xs" v-show="!paused"/>
          </span>
        </button>
      </div>
      <!-- <textarea
        class="textarea has-fixed-size"
        :disabled="state.rootKani?.state !== RunState.stopped"
        autofocus
        rows="1"
        ref="chatInput"
        v-model.trim="chatMsg"
        @keydown.enter.exact.prevent="sendChatMsg"
      ></textarea> -->
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
