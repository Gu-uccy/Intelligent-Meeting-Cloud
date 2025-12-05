<script setup>
import LayoutNav from './components/LayoutNav.vue'
import LayoutFooter from './components/LayoutFooter.vue'
import SideBar from './components/SideBar.vue'
</script>

<template>
  <div class="app">
    <LayoutNav />
    <SideBar />
    <main class="main">
      <RouterView />
    </main>
    <LayoutFooter />
  </div>
</template>

<style scoped>
.app { min-height:100vh; display:flex; flex-direction:column; }
.main {
  flex:1;
  margin-top:60px;
  margin-left:200px;
  padding:2rem;
  background:#f7f8fa;
}
@media (max-width: 767px) {
  .main { margin-left:0; padding:1rem; }
}
</style>