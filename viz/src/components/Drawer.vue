<script setup lang="ts">
import LoadSaveModal from "@/components/LoadSaveModal.vue";
import SessionMetaRow from "@/components/SessionMetaRow.vue";
import { API } from "@/redel/api";
import type { SessionMeta } from "@/redel/models";
import { sorted } from "@/redel/utils";
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";

const router = useRouter();

const isOpen = ref<boolean>(true);
const loadSaveModal = ref<InstanceType<typeof LoadSaveModal> | null>(null);
const interactiveSessions = ref<SessionMeta[]>([]);


const showInstructions = ref(false); 
const selectedSessionId = ref<string | null>(null); 

async function startNewInteractive() {
  // soojin -- changed to disable new session
  console.warn("Starting new sessions has been disabled.");
}

async function updateInteractive() {
  interactiveSessions.value = await API.listStatesInteractive();
  // PAL stuff - if we don't have the interactive states we want, make them
  if (interactiveSessions.value.length < 3) {
    await API.initPalStates();
    interactiveSessions.value = await API.listStatesInteractive();
  }
}

async function resetUserId() {
  const conf = confirm("Are you sure? This will reset all patient states!");
  if (!conf) return;
  API.resetUid();
  router.push({ name: "home" });
}


function handleSessionClick(sessionId: string) { 
  selectedSessionId.value = sessionId; 
  // Check if the popup has already been shown in this session
  if (!sessionStorage.getItem("popupShown")) { // NEW
    showInstructions.value = true;             // NEW
    sessionStorage.setItem("popupShown", "true"); // NEW
  } else {                                     // NEW
    proceedToSession();                        // NEW
  }
}

// when clicked start start session, otehrwise stay in current state
function proceedToSession() { 
  if (selectedSessionId.value) { 
    router.push({ name: "interactive", params: { sessionId: selectedSessionId.value } }); 
    showInstructions.value = false;
    selectedSessionId.value = null; 
  }
}


// hooks
onMounted(async () => {
  await updateInteractive();
});
router.afterEach(async () => {
  // update the session list on each navigation
  await updateInteractive();
});
</script>

<template>
  <aside class="menu drawer h-100" :class="{ closed: !isOpen, open: isOpen }">
    <div class="is-clipped">
      <div class="fixed-drawer-width">
        <RouterLink class="title" to="/">PAL</RouterLink>
        <p class="menu-label">Controls</p>
        <ul class="menu-list">
          <!--  soojin - Disable new session
          <li>
            <a @click="startNewInteractive">
              <span class="icon-text">
                <span class="icon is-small mt-1">
                  <font-awesome-icon :icon="['fas', 'circle-plus']" />
                </span>
                <span>Start a new session</span>
              </span>
            </a>
          </li>
        -->
          <li>
            <a @click="loadSaveModal!.open()">
              <span class="icon-text">
                <span class="icon is-small mt-1">
                  <font-awesome-icon :icon="['fas', 'folder-open']" />
                </span>
                <span>Load a saved session</span>
              </span>
            </a>
          </li>
        </ul>

        <p class="menu-label">Interactive Sessions</p>
        <ul class="menu-list">
          <li
            v-for="session in sorted(
              interactiveSessions,
              (a: SessionMeta, b: SessionMeta) => b.last_modified - a.last_modified,
            )"
          >
              <a @click="handleSessionClick(session.id)">
              <SessionMetaRow :data="session" hide-icon-hints />
              </a>
          </li>
          <li v-if="!interactiveSessions.length">
            <a> None yet! </a>
          </li>
        </ul>

        <p class="menu-label">User Info</p>
        <ul class="menu-list">
          <li>
            <a> Your user ID: {{ API.uid }} </a>
          </li>
          <li>
            <a @click="resetUserId"> Reset user ID </a>
          </li>
        </ul>
      </div>
    </div>

    <div class="drawer-handle has-text-weight-bold has-text-centered is-unselectable" @click="isOpen = !isOpen">
      {{ isOpen ? "&lt;" : "&gt;" }}
    </div>
  </aside>

  <LoadSaveModal ref="loadSaveModal" />
  <div v-if="showInstructions" class="modal is-active"> 
    <div class="modal-background"></div>
    <div class="modal-card">
      <header class="modal-card-head">
        <p class="modal-card-title">How to Start?</p>
        <button class="delete" aria-label="close" @click="showInstructions = false"></button> <!-- Close Modal -->
      </header>
      <section class="modal-card-body">
        <p><strong>Patient Context:</strong> Read the patient profile for context.</p>
        <p><strong>Interaction Modes:</strong> Toggle between Speech and Text Input.</p>
        <p><strong>Feedback:</strong> Use the "Feedback" button to end the conversation and provide feedback.</p>
        <p><strong>Restarting:</strong> Use the "Reset User ID" button to restart a session.</p>
      </section>
      <footer class="modal-card-foot">
        <button class="button is-primary" @click="proceedToSession">Start</button> <!-- Start session -->
      </footer>
    </div>
  </div>
</template>

<style scoped lang="scss">
@import "@/global.scss";

$drawer-width: 16rem;
$drawer-padding: 1rem;
$handle-width: 0.75rem;
$handle-height: 3rem;

.drawer {
  position: relative;
  background-color: rgba($beige-light, 0.4);
  transition: width 300ms;
}

.open {
  width: $drawer-width;
}

.closed {
  width: 0;
}

.drawer-handle {
  position: absolute;
  right: -$handle-width;
  top: 50%;
  width: $handle-width;
  height: $handle-height;
  line-height: $handle-height;
  vertical-align: middle;
  border-radius: 0 4px 4px 0;
  background-color: rgba($beige-light, 0.5);
}

.drawer-handle:hover {
  background-color: rgba($beige-light, 1);
}

.fixed-drawer-width {
  width: $drawer-width - ($drawer-padding * 2);
  margin: $drawer-padding;
  overflow: hidden;
}
</style>
