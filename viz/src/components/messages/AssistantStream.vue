<script setup lang="ts">
import Markdown from "@/components/Markdown.vue";

const props = defineProps<{
  content: string;
  img?: string; // Dynamic image URL passed from ChatMessages.vue
}>();
</script>

<template>
  <div class="media">
    <figure class="media-left">
      <p class="image is-32x32">
        <img :src="img" alt="Assistant Stream" />
      </p>
    </figure>
    <div class="media-content">
      <div class="content allow-wrap-anywhere">
        <Markdown :content="props.content" />
        <slot></slot>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
@import "./messages.scss";
</style>
