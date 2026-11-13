<script setup>
const currentYear = new Date().getFullYear();
</script>

<template>
  <footer class="app-footer">
    <div class="content">
      <p>
        © {{ currentYear }} 智会云 (SmartMeeting). All rights reserved. 
        <span>|</span> 
        <a href="#">隐私政策</a>
      </p>
    </div>
  </footer>
</template>

<style scoped>
.app-footer {
  width: 100%;
  padding: 20px 0;
  text-align: center;
  background: transparent; 
  margin-top: auto;
}

.content {
  color: #888;
  font-size: 0.85rem;
}

.content span {
  margin: 0 10px;
  color: #ccc;
}

.content a {
  color: #20ae7c;
  text-decoration: none;
  transition: 0.3s;
}

.content a:hover {
  color: #04befe;
}
</style>
