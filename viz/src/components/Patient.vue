<script setup>
import {inject, onMounted, onUnmounted, ref, watch} from "vue";

const props = defineProps(['name', 'age', 'gender', 'img']);
</script>

<template>
    <img :src="`${props.img}`" alt="Patient Image"/>
    <div class="description-container">
        <p><strong> {{ props.name }} </strong>, {{ props.age }}{{ props.gender }}</p>
        <!-- <p>{{ props.gender.toUpperCase()[0] + props.gender.slice(1) }}</p> -->
    </div>
</template>

<style scoped>
</style>
