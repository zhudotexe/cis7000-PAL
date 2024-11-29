<script setup lang="ts">
import AssistantMessage from "@/components/messages/AssistantMessage.vue";
import AssistantStream from "@/components/messages/AssistantStream.vue";
import AssistantThinking from "@/components/messages/AssistantThinking.vue";
import FunctionMessage from "@/components/messages/FunctionMessage.vue";
import SystemMessage from "@/components/messages/SystemMessage.vue";
import UserMessage from "@/components/messages/UserMessage.vue";
import { ChatRole, type KaniState, RunState } from "@/redel/models";
import type { ReDelState } from "@/redel/state";
import { computed, inject, ref } from "vue";

const props = defineProps<{
  kani: KaniState;
}>();

const state = inject<ReDelState>("state")!;
const chatHistory = ref<HTMLElement | null>(null);

// Computed property for consistent dynamic image retrieval
const patientImageUrl = computed(() => {
  return state.meta?.extra?.patient_image_url || '/faces/nervous.png'; // Fallback image
});

function scrollChatToBottom() {
  if (chatHistory.value === null) return;
  chatHistory.value.scrollTop = chatHistory.value.scrollHeight;
}

defineExpose({ scrollChatToBottom });
</script>

<template>
  <div class="messages" ref="chatHistory">
    <!-- Complete messages -->
    <div v-for="message in kani.chat_history" class="chat-message">
      <UserMessage 
        v-if="message.role === ChatRole.user" 
        :message="message" 
        class="user" 
      />
      <AssistantMessage 
        v-else-if="message.role === ChatRole.assistant" 
        :message="message" 
        :img="patientImageUrl" 
      />
      <FunctionMessage 
        v-else-if="message.role === ChatRole.function" 
        :message="message" 
      />
      <SystemMessage 
        v-else-if="message.role === ChatRole.system" 
        :message="message" 
      />
    </div>

    <!-- Stream buffer -->
    <div class="chat-message" v-if="streamBuffer">
      <AssistantStream 
        :content="streamBuffer"
        :img="patientImageUrl"
      />
    </div>

    <!-- Assistant thinking -->
    <div class="chat-message" v-if="kani.state !== RunState.stopped && !streamBuffer">
      <AssistantThinking 
        :img="patientImageUrl"
      />
    </div>

    <div class="scroll-anchor"></div>
  </div>
</template>

<style scoped>
.messages {
  padding: 4rem 4rem 2rem 4rem;
  overflow-y: auto;
}

.chat-message {
  overflow-anchor: none;
}

.chat-message > * {
  padding: 0.5em;
}

.scroll-anchor {
  height: 1px;
  overflow-anchor: auto;
}
</style>
