<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router' 

const route = useRoute()

const breadcrumbs = computed(() => {
  return route.matched
    .filter(item => item.meta && item.meta.title)
    .map(item => ({
      path: item.path,
      title: item.meta.title
    }))
})
</script>

<template>
  <div class="breadcrumb">
    <template v-for="(item, index) in breadcrumbs" :key="item.path">
      <span v-if="index === breadcrumbs.length - 1">{{ item.title }}</span>

      <router-link v-else :to="item.path">{{ item.title }}</router-link>
      
      <span v-if="index < breadcrumbs.length - 1">/</span>
    </template>
  </div>
</template>

<style scoped lang="scss">
.breadcrumb {
  display: flex;
  align-items: center;
  font-size: 0.9rem;
  color: #64748b; 
  
  a {
    color: #475569;
    text-decoration: none;
    transition: color 0.2s;
    &:hover {
      color: #35bc88;
    }
  }
  
  span {
    margin: 0 0.5rem;
    color: #cbd5e1;
  }
  
  span:last-child {
    color: #1e293b;
    font-weight: 500;
  }
}

@media (max-width: 767px) { 
  .breadcrumb { 
    display: none; 
  }
}
</style>