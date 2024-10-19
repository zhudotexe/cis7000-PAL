<script setup>
import {inject, onMounted, onUnmounted, ref, watch} from "vue";

const props = defineProps(['name', 'age', 'gender']);
</script>

<template>
    <img src="@/assets/faces/nervous.png" alt="Patient Image"/>
    <div class="description-container">
        <p><strong> {{ props.name }} </strong>, {{ props.age }}</p>
        <p>{{ props.gender.toUpperCase()[0] + props.gender.slice(1) }}</p>
    </div>
</template>

<style scoped>
</style>
