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
  // soojin -- disable users from making new session
  console.warn("Starting new sessions has been disabled.");
}

async function updateInteractive() {
  interactiveSessions.value = await API.listStatesInteractive();
  if (interactiveSessions.value.length < 3) {
    await API.initPalStates();
    interactiveSessions.value = await API.listStatesInteractive();
  }
}

async function resetUserId() {
  const conf = confirm("Are you sure? This will reset all patient states!");
  if (!conf) return;
  sessionStorage.removeItem("popupShown");  // Reset sessionStorage for popup
  API.resetUid();
  router.push({ name: "home" });
}


function handleSessionClick(sessionId: string) { 
  selectedSessionId.value = sessionId; 
  console.log("Session clicked:", sessionId);

  // Show popup only if not already shown in this session
  if (!sessionStorage.getItem("popupShown")) {
    showInstructions.value = true; // Show the popup
    sessionStorage.setItem("popupShown", "true"); // Mark popup as shown
    console.log("Popup displayed after session click.");
  } else {
    console.log("Popup already shown for this session.");
    proceedToSession(); // Directly proceed if popup was already shown
  }
}

function proceedToSession() { 
  if (selectedSessionId.value) { 
    router.push({ name: "interactive", params: { sessionId: selectedSessionId.value } }); 
    showInstructions.value = false; // Hide popup
    selectedSessionId.value = null; 
  }
}


onMounted(async () => {
  console.log("Page mounted, updating interactive sessions...");
  await updateInteractive();
});

router.afterEach(async () => {
  console.log("Route changed, updating interactive sessions...");
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
        <button class="delete" aria-label="close" @click="showInstructions = false"></button> 
      </header>
      <section class="modal-card-body">
        <p><strong>Patient Context:</strong> Review the patient profile in the right panel.</p>
        <p><strong>Interaction Modes:</strong> Toggle between Speech and Text Input (top-right)</p>
        <p><strong>Feedback:</strong> Use "End Session" button to end the conversation and provide feedback.</p>
        <p><strong>Restart:</strong> Click "Reset User ID" button to restart a session.</p>
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
