<script setup lang="ts">
import Chat from "@/components/Chat.vue";
import ChatMessages from "@/components/ChatMessages.vue";
import Patient from "@/components/Patient.vue";
import PatientState from "@/components/PatientState.vue";
import Tree from "@/components/Tree.vue";
import { InteractiveClient } from "@/pal/interactive-openai";
import type { KaniState } from "@/redel/models";
import { Notifications } from "@/redel/notifications";
import { onMounted, onUnmounted, provide, reactive, ref } from "vue";
import { useRouter } from "vue-router";

const props = defineProps<{
  sessionId: string;
}>();

const router = useRouter();

const client = reactive(new InteractiveClient(props.sessionId));
const introspectedKani = ref<KaniState | null>(null);
const tree = ref<InstanceType<typeof Tree> | null>(null);
const patient = ref<InstanceType<typeof Patient> | null>(null);
const patientData = {
  name: "Sarah Smith",
  age: "38",
  gender: "nonbinary"
}

provide("client", client);
provide("state", client.state);

// hooks
onMounted(async () => {
  // update tree on messages and state changes
  client.events.addEventListener("kani_message", () => tree.value?.update());
  client.events.addEventListener("kani_state_change", () => tree.value?.updateColors());

  // connect ws to backend, get state, update tree
  const resp = await client.getState();
  // if this failed (e.g. user bookmarks a state), notify and redir to save
  if (!resp.success) {
    Notifications.info("This session is no longer active - you are viewing its replay."); // todo instructions to restart it
    router.push({ name: "save", params: { saveId: props.sessionId } });
    return;
  }
  client.connect();
  tree.value?.update();
});
onUnmounted(() => client.close());
</script>

<template>
  <div class="main">
    <div class="columns is-gapless h-100">
      <!-- root chat -->
      <div class="column">
        <div class="header-container">
          <Patient :name="patientData.name" :age="patientData.age" :gender="patientData.gender" ref="patient" />
        </div>
        <div class="left-container chat-container">
          <Chat class="mt-auto" />
        </div>
      </div>
      <!-- viz -->
      <div class="column">
        <div class="right-container is-flex is-flex-direction-column">
          <p class="subtitle feedback-title">Feedback and Patient State Dashboard</p>
          <PatientState :affectValence="30" :affectArousal="32" :affectDominance="20" />
          <!-- <div class="is-flex-shrink-0">
            <Tree
              @node-clicked="(id) => (introspectedKani = client.state.kaniMap.get(id) ?? null)"
              :selected-id="introspectedKani?.id"
              ref="tree"
            />
          </div>
          <p v-if="introspectedKani" class="has-text-centered">
            Selected: {{ introspectedKani.name }}-{{ introspectedKani.depth }}
          </p>
          <div class="introspection-container">
            <ChatMessages :kani="introspectedKani" v-if="introspectedKani" />
            <p v-else>Click on a node on the tree above to view its state.</p>
          </div> -->
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
@import "@/global.scss";

$header-height: 8rem;

.main {
  height: 100vh;
}
.column:last-child {
  max-width: 300px;
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

.introspection-container {
  padding: 0 2rem;
  min-height: 0;
  overflow-y: auto;
}
</style>
