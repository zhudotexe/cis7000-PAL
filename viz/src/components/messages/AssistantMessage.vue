<script setup lang="ts">
import Markdown from "@/components/Markdown.vue";
import AssistantFunctionCall from "@/components/messages/AssistantFunctionCall.vue";
import type { ChatMessage } from "@/redel/models";

// Default fallback image

const props = defineProps<{
  message: ChatMessage;
  img?: string; // Dynamic image URL passed from ChatMessages.vue
}>();
</script>

<template>
  <div class="media">
    <figure class="media-left">
      <p class="image is-48x48">
        <img :src="img" alt="Assistant" />
      </p>
    </figure>
    <div class="media-content">
      <div class="content allow-wrap-anywhere" v-if="message.content">
        <Markdown :content="props.message.content!" />
      </div>
      <!-- function call -->
      <div v-if="message.tool_calls">
        <AssistantFunctionCall :function-call="tc.function" v-for="tc in message.tool_calls" />
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
@import "./messages.scss";
</style>
