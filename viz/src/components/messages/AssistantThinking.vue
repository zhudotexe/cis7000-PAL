<script setup lang="ts">
const props = defineProps<{
  img?: string; // Dynamic image passed from parent
}>();
</script>

<template>
  <div class="media">
    <figure class="media-left">
      <p class="image is-32x32">
        <!-- Use dynamic image or fallback -->
        <img :src="img" alt="Assistant Thinking" />
      </p>
    </figure>
    <div class="media-content">
      <div class="content">
        <span class="loader mt-2"></span>
      </div>
    </div>
  </div>
</template>

<style scoped></style>

