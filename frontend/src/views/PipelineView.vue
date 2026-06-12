<template>
  <div class="pipeline-page">
    <!-- 输入区域 -->
    <el-card class="input-card">
      <template #header>
        <span>配置测试参数</span>
      </template>

      <el-form :model="form" label-width="100px">
        <el-form-item label="API 文档">
          <el-input
            v-model="form.api_doc"
            type="textarea"
            :rows="8"
            placeholder="粘贴 API 文档内容，例如：&#10;POST /api/users/register&#10;参数: username(string,3-20字符), email(string,邮箱格式), password(string,6-128字符)&#10;成功: 201, 错误: 400/409/422"
          />
        </el-form-item>

        <el-form-item label="被测地址">
          <el-input v-model="form.base_url" placeholder="http://127.0.0.1:8080" />
        </el-form-item>

        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="AI 模型">
              <el-select v-model="form.model" style="width: 100%">
                <el-option label="DeepSeek V4 Flash（快速）" value="deepseek" />
                <el-option label="DeepSeek V4 Pro（高质量）" value="deepseek-pro" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="项目名称">
              <el-input v-model="form.project_name" placeholder="My API Project" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item>
          <el-button
            type="primary"
            :loading="running"
            :disabled="!form.api_doc || !form.base_url"
            @click="startPipeline"
          >
            <el-icon><VideoPlay /></el-icon>
            开始测试
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 进度展示 -->
    <el-card v-if="taskId" class="progress-card">
      <template #header>
        <span>执行进度</span>
      </template>

      <el-steps :active="currentStep" finish-status="success" align-center>
        <el-step title="生成用例" description="AI 分析文档" />
        <el-step title="执行测试" description="pytest 运行" />
        <el-step title="分析失败" description="AI 归因" />
        <el-step title="生成报告" description="汇总结果" />
      </el-steps>

      <div class="progress-message" v-if="progressMessage">
        <el-icon class="is-loading" v-if="running"><Loading /></el-icon>
        {{ progressMessage }}
      </div>

      <div v-if="error" class="error-message">
        <el-alert :title="error" type="error" show-icon :closable="false" />
      </div>
    </el-card>

    <!-- 结果展示 -->
    <el-card v-if="result" class="result-card">
      <template #header>
        <div class="result-header">
          <span>测试报告</span>
          <el-tag :type="passRateType" size="large">
            通过率 {{ (result.summary.pass_rate * 100).toFixed(1) }}%
          </el-tag>
        </div>
      </template>

      <!-- 摘要统计 -->
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

      <!-- 用例详情表格 -->
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
        <el-table-column prop="category" label="分类" width="100" />
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

      <!-- 生成的用例列表（可折叠） -->
      <el-collapse style="margin-top: 20px">
        <el-collapse-item title="查看 AI 生成的测试用例" name="cases">
          <el-table :data="result.test_cases_generated" stripe size="small">
            <el-table-column prop="name" label="用例名" min-width="200" />
            <el-table-column prop="method" label="方法" width="70" />
            <el-table-column prop="url" label="路径" width="180" />
            <el-table-column prop="expected_status" label="期望状态码" width="100" />
            <el-table-column prop="category" label="分类" width="100" />
            <el-table-column prop="description" label="描述" min-width="200" />
          </el-table>
        </el-collapse-item>
      </el-collapse>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { VideoPlay, Loading } from '@element-plus/icons-vue'
import { runPipeline, getPipelineStatus } from '../api'
import { ElMessage } from 'element-plus'

const form = ref({
  api_doc: '',
  base_url: 'http://127.0.0.1:8080',
  model: 'deepseek-pro',
  project_name: 'HappyTest',
})

const running = ref(false)
const taskId = ref('')
const currentStep = ref(0)
const progressMessage = ref('')
const error = ref('')
const result = ref(null)

const passRateType = computed(() => {
  if (!result.value) return 'info'
  const rate = result.value.summary.pass_rate
  if (rate >= 0.8) return 'success'
  if (rate >= 0.5) return 'warning'
  return 'danger'
})

let pollTimer = null

async function startPipeline() {
  running.value = true
  error.value = ''
  result.value = null
  currentStep.value = 0
  progressMessage.value = '提交中...'

  try {
    const res = await runPipeline(form.value)
    taskId.value = res.task_id
    startPolling()
  } catch (e) {
    error.value = e.message
    running.value = false
  }
}

function startPolling() {
  pollTimer = setInterval(async () => {
    try {
      const status = await getPipelineStatus(taskId.value)

      // 更新进度
      if (status.progress) {
        currentStep.value = status.progress.step - 1
        progressMessage.value = status.progress.message
      }

      // 完成
      if (status.status === 'completed') {
        stopPolling()
        running.value = false
        currentStep.value = 4
        progressMessage.value = ''
        result.value = status.result
        ElMessage.success('测试执行完成')
      }

      // 失败
      if (status.status === 'failed') {
        stopPolling()
        running.value = false
        error.value = status.error || '执行失败'
        ElMessage.error('执行失败: ' + error.value)
      }
    } catch (e) {
      stopPolling()
      running.value = false
      error.value = '查询状态失败: ' + e.message
    }
  }, 2000) // 每 2 秒轮询一次
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}
</script>

<style scoped>
.pipeline-page {
  max-width: 1200px;
  margin: 0 auto;
}

.input-card,
.progress-card,
.result-card {
  margin-bottom: 20px;
}

.progress-message {
  text-align: center;
  margin-top: 20px;
  color: #606266;
  font-size: 14px;
}

.error-message {
  margin-top: 16px;
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