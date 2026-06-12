<template>
  <div class="report-page">
    <el-page-header @back="$router.push('/')" title="返回" content="测试报告" />

    <div v-if="loading" class="loading-state">
      <el-icon class="is-loading" :size="32"><Loading /></el-icon>
      <p>加载报告中...</p>
    </div>

    <el-alert v-else-if="error" :title="error" type="error" show-icon :closable="false" style="margin-top: 20px" />

    <template v-else-if="result">
      <el-card class="result-card">
        <template #header>
          <div class="result-header">
            <span>执行结果</span>
            <el-tag :type="passRateType" size="large">
              通过率 {{ (result.summary.pass_rate * 100).toFixed(1) }}%
            </el-tag>
          </div>
        </template>

        <el-row :gutter="16" class="summary-row">
          <el-col :span="6">
            <el-statistic title="总计" :value="result.summary.total" />
          </el-col>
          <el-col :span="6">
            <el-statistic title="通过" :value="result.summary.passed" class="stat-passed" />
          </el-col>
          <el-col :span="6">
            <el-statistic title="失败" :value="result.summary.failed" class="stat-failed" />
          </el-col>
          <el-col :span="6">
            <el-statistic title="耗时" :value="result.summary.duration.toFixed(2) + 's'" />
          </el-col>
        </el-row>

        <el-table :data="result.cases" stripe style="width: 100%; margin-top: 20px">
          <el-table-column prop="name" label="用例名称" min-width="200" />
          <el-table-column prop="status" label="状态" width="80">
            <template #default="{ row }">
              <el-tag :type="row.status === 'passed' ? 'success' : 'danger'" size="small">
                {{ row.status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="duration" label="耗时" width="80">
            <template #default="{ row }">
              {{ row.duration.toFixed(3) }}s
            </template>
          </el-table-column>
          <el-table-column label="失败原因" min-width="250">
            <template #default="{ row }">
              <span v-if="row.ai_analysis?.root_cause" class="analysis-text">
                <el-tag size="small" type="warning">{{ row.ai_analysis.category }}</el-tag>
                {{ row.ai_analysis.root_cause }}
              </span>
              <span v-else-if="row.failure_reason" class="failure-text">
                {{ row.failure_reason.slice(0, 100) }}
              </span>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </template>

    <div v-else class="empty-state">
      <el-empty description="该任务尚未完成或不存在" />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { Loading } from '@element-plus/icons-vue'
import { getPipelineStatus } from '../api'

const route = useRoute()

const loading = ref(true)
const error = ref('')
const result = ref(null)

const passRateType = computed(() => {
  if (!result.value) return 'info'
  const rate = result.value.summary.pass_rate
  if (rate >= 0.8) return 'success'
  if (rate >= 0.5) return 'warning'
  return 'danger'
})

onMounted(async () => {
  try {
    const status = await getPipelineStatus(route.params.taskId)
    if (status.status === 'completed') {
      result.value = status.result
    } else if (status.status === 'failed') {
      error.value = status.error || '该任务执行失败'
    }
  } catch (e) {
    error.value = '加载报告失败: ' + e.message
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.report-page {
  max-width: 1200px;
  margin: 0 auto;
}

.result-card {
  margin-top: 20px;
}

.loading-state {
  text-align: center;
  padding: 60px 0;
  color: #909399;
}

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.summary-row {
  text-align: center;
  padding: 16px 0;
}

.stat-passed :deep(.el-statistic__number) {
  color: #67c23a;
}

.stat-failed :deep(.el-statistic__number) {
  color: #f56c6c;
}

.analysis-text {
  font-size: 13px;
  color: #606266;
}

.failure-text {
  font-size: 12px;
  color: #909399;
  font-family: monospace;
}
</style>
