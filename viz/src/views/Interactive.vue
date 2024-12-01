<script setup lang="ts">
import Chat from "@/components/Chat.vue";
import Patient from "@/components/Patient.vue";
import PatientState from "@/components/PatientState.vue";
import { InteractiveClient } from "@/pal/interactive-openai";
import { Notifications } from "@/redel/notifications";
import { onMounted, onUnmounted, provide, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import Markdown from "@/components/Markdown.vue";

const props = defineProps<{
  sessionId: string;
}>();

const router = useRouter();

const client = reactive(new InteractiveClient(props.sessionId));
const patient = ref<InstanceType<typeof Patient> | null>(null);

provide("client", client);
provide("state", client.state);

const isSpeechEnabled = ref(true);
const chat = ref<InstanceType<typeof Chat> | null>(null);

// hooks
onMounted(async () => {
  // connect ws to backend, get state, update tree
  const resp = await client.getState();
  // if this failed (e.g. user bookmarks a state), notify and redir to save
  if (!resp.success) {
    Notifications.info("This session is no longer active - you are viewing its replay."); // todo instructions to restart it
    router.push({ name: "save", params: { saveId: props.sessionId } });
    return;
  }
  client.connect();
  console.log(client.state.meta?.extra);
});
onUnmounted(() => client.close());

function toggleSpeech() {
  isSpeechEnabled.value = !isSpeechEnabled.value;
  chat.value?.toggleSpeech();
}
function endInteraction() {
  if (chat.value?.isEnded) return;

  var transcript = "";
  for (const msg of client.state.rootMessages) {
    if (msg.role === "user") {
      transcript += "Doctor: " + msg.content + "\n";
    } else if (msg.role === "assistant") {
      transcript += "Patient: " + msg.content + "\n";
    }
  }

  chat.value?.end();
  client.endSession(transcript);
}
</script>

<template>
  <div class="main">
    <div class="columns is-gapless h-100">
      <!-- root chat -->
      <div class="column">
        <div class="header-container">
          <Patient 
          :name="client.state.meta?.extra?.patient_name ?? 'No patient name'" 
          :age="client.state.meta?.extra?.patient_age ?? 'No patient age'" 
          :gender="client.state.meta?.extra?.patient_gender ?? 'No patient gender'" 
          :img="client.state.meta?.extra?.patient_image_url ?? '@/assets/faces/nervous.png'"
          ref="patient" 
        />
        </div>
        <div class="left-container chat-container">
          <Chat class="mt-auto" ref="chat"/>
        </div>
      </div>
      <!-- viz -->
      <div class="column">
        <div class="right-container is-flex is-flex-direction-column">
          <!-- <p class="subtitle feedback-title">Feedback and Patient State Dashboard</p>
          <PatientState :affectValence="30" :affectArousal="32" :affectDominance="20" /> -->
          <!-- TODO(allen): make this look nice -->
           <div class="flex content">
            <h4>Speech Mode:</h4>
            <label class="switch">
                <input type="checkbox" :checked="isSpeechEnabled" @change="toggleSpeech">
              <span class="slider round"></span>
            </label>
           </div>
           <br>
           <div>
            <button @click="endInteraction">Finish Session</button>
           </div>
           <hr>
          <Markdown class="content" :content="client.state.meta?.extra?.patient_info ?? 'No patient info'" />
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
@import "@/global.scss";

$header-height: 8rem;

button {
  background-color: $purple;
  border: none;
  width: 100%;
  border-radius: 0.5rem;

  color: white;
  padding: 0.5rem 1rem;
  cursor: pointer;

  &:hover {
    background-color: darken($purple, 10%);
  }
}

.main {
  height: 100vh;
}

.column:last-child {
  max-width: 300px;
  height: 100%;

  overflow-y: scroll;
}

.header-container {
  display: flex;
  height: $header-height;
  padding: 2rem 4rem 2rem 4rem;
  background-color: rgba($beige-light, 0.8);

  justify-content: flex-start;
  column-gap: 1rem;
}

.left-container {
  height: calc(100% - $header-height);
  background-color: rgba($beige-light, 0.2);
}

.chat-container {
  min-height: 0;
}

.right-container {
  max-height: 100%;
  padding: 2rem;
}

.feedback-title {
  text-align: center;
  font-weight: bold;
}

.right-container {
  hr {
    border: 1px solid gray;
    margin: 15px 0;
  }
  h2 {
    font-size: 1rem;
  }
}
.flex.content {
  display: flex;
  justify-content: space-between;
  margin-bottom: 0;

  h4 {
    margin: 0;
  }
}
/* The switch - the box around the slider */
.switch {
  position: relative;
  display: inline-block;
  width: 48px;
  height: 25px;
}

/* Hide default HTML checkbox */
.switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

/* The slider */
.slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: #ccc;
  -webkit-transition: .4s;
  transition: .4s;
}

.slider:before {
  position: absolute;
  content: "";
  height: 20px;
  width: 20px;
  left: 4px;
  bottom: 0;
  top: 2px;
  background-color: white;
  -webkit-transition: .4s;
  transition: .4s;
}

input:checked + .slider {
  background-color: $purple;
}

input:focus + .slider {
  box-shadow: 0 0 1px $purple;
}

input:checked + .slider:before {
  -webkit-transform: translateX(20px);
  -ms-transform: translateX(20px);
  transform: translateX(20px);
}

/* Rounded sliders */
.slider.round {
  border-radius: 34px;
}

.slider.round:before {
  border-radius: 50%;
}
</style>
