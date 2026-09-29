<script setup lang="ts">
import cmgc from '@/assets/brand/CMGC.png'
import logo from '@/assets/brand/logo.png'
import tjbridge from '@/assets/brand/TJBridge.png'
</script>

<template>
  <div class="home">
    <div class="home-top">
      <img :src="cmgc" alt="CMGC" class="home-cmgc" />
      <img :src="logo" alt="logo" class="home-logo" />
    </div>
    <h1 class="home-title">三维扫描分析系统</h1>
    <h2 class="home-subtitle">DeviScan-3D V1.0</h2>
    <img :src="tjbridge" alt="TJBridge" class="home-tjbridge" />
    <p class="home-footer">Updata on:2025/07/23</p>
  </div>
</template>

<style scoped>
.home {
  max-width: 880px;
  margin: 0 auto;
  text-align: center;
}

.home-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.home-cmgc {
  height: 96px;
  object-fit: contain;
}

.home-logo {
  height: 56px;
  object-fit: contain;
}

.home-title {
  color: steelblue;
  font-size: 44px;
  margin-top: 64px;
}

.home-subtitle {
  color: lightslategray;
  font-size: 32px;
  margin: 12px 0 40px;
}

.home-tjbridge {
  max-width: 560px;
}

.home-footer {
  color: gray;
  font-size: 12px;
  margin-top: 24px;
}
</style>
