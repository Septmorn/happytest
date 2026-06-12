<template>
  <el-container class="app-container">
    <el-header class="app-header">
      <div class="header-left">
        <h1 class="app-title">HappyTest</h1>
        <span class="app-subtitle">AI 驱动的 API 自动化测试平台</span>
      </div>
      <el-menu
        mode="horizontal"
        :default-active="$route.path"
        router
        class="header-menu"
      >
        <el-menu-item index="/pipeline">
          <el-icon><VideoPlay /></el-icon>
          执行测试
        </el-menu-item>
      </el-menu>
    </el-header>
    <el-main class="app-main">
      <router-view />
    </el-main>
  </el-container>
</template>

<script setup>
import { VideoPlay } from '@element-plus/icons-vue'
</script>

<style>
body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

.app-container {
  min-height: 100vh;
}

.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid #e4e7ed;
  padding: 0 24px;
}

.header-left {
  display: flex;
  align-items: baseline;
  gap: 12px;
}

.app-title {
  font-size: 20px;
  margin: 0;
  color: #303133;
}

.app-subtitle {
  font-size: 13px;
  color: #909399;
}

.header-menu {
  border-bottom: none;
}

.app-main {
  padding: 24px;
  background: #f5f7fa;
}
</style>