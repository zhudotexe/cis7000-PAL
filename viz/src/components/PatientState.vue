<script setup>
import {inject, onMounted, onUnmounted, ref, watch} from "vue";

const props = defineProps(['affectValence', 'affectArousal', 'affectDominance']);
const affectValence = ref(props.affectValence);
const affectArousal = ref(props.affectArousal);
const affectDominance = ref(props.affectDominance);
</script>

<template>

    <p class="subtitle">Affective State</p>
    <div>
        <p>Valence</p>
        <input type="range" class="valence" v-model="affectValence">
        <p>Arousal</p>
        <input type="range" class="arousal" v-model="affectArousal">
        <p>Dominance</p>
        <input type="range" class="dominance" v-model="affectDominance">
    </div>
</template>

<style scoped lang="scss">
input[type="range"] {
  appearance: none;
  width: 100%;
  height: 8px;
  border-radius: 5px;
}
input[type="range"]::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  height: 20px;
  width: 20px;
  border-radius: 50%;
  background: white;
  cursor: pointer;

  box-shadow: 0 0 2px 2px rgba(black, 0.1);
}

.valence {
  background: linear-gradient(to right, #350d9a, #dc1e61);
}
.arousal {
  background: linear-gradient(to right, #92c10c, #dc7f1e);
}
.dominance {
  background: linear-gradient(to right, #28b0bb, #750869);
}
</style>
