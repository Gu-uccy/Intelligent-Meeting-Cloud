<script setup>
import { ref } from 'vue'

const props = defineProps({
  show: {
    type: Boolean,
    default: false
  },
  title: {
    type: String,
    default: '标题'
  },
  width: {
    type: String,
    default: '500px' // 支持自定义宽度
  }
})

const emit = defineEmits(['close', 'submit'])

// 标记变量：记录鼠标是否是真的在遮罩层上按下的
const isPressedOnOverlay = ref(false)

// 1. 鼠标按下
const handleMouseDown = (e) => {
  // 如果点击的是遮罩层本身 (e.target === e.currentTarget)
  if (e.target === e.currentTarget) {
    isPressedOnOverlay.value = true
  } else {
    isPressedOnOverlay.value = false
  }
}

// 2. 鼠标抬起
const handleMouseUp = (e) => {
  // 只有当：起点是遮罩层 && 终点也是遮罩层，才关闭
  if (isPressedOnOverlay.value && e.target === e.currentTarget) {
    emit('close')
  }
  
  // 重置状态
  isPressedOnOverlay.value = false
}
</script>

<template>
  <Teleport to="body">
    <Transition name="fade">
      <div 
        v-if="show" 
        class="modal-overlay"
        @mousedown="handleMouseDown"
        @mouseup="handleMouseUp"
      >
        <!-- 这里的 @click.stop 可以留着，作为双重保险，也可以不加 -->
        <div class="modal-container" :style="{ width: width }" @click.stop>
          
          <!-- 头部 -->
          <div class="modal-header">
            <h3>{{ title }}</h3>
            <button class="close-btn" @click="emit('close')">
              <i class="fas fa-times"></i>
            </button>
          </div>
          
          <!-- 内容 -->
          <div class="modal-body">
            <slot></slot>
          </div>
          
          <!-- 底部 (可选) -->
          <div class="modal-footer">
            <button class="btn-cancel" @click="emit('close')">取消</button>
            <button class="btn-confirm" @click="emit('submit')">确定</button>
          </div>

        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(3px);
  z-index: 999;
  display: flex;
  justify-content: center;
  align-items: center;
}

.modal-container {
  /* 修改：背景改为白色 */
  background: #ffffff; 
  border-radius: 12px;
  /* 修改：边框改为浅灰 */
  border: 1px solid #e2e8f0; 
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1);
  display: flex;
  flex-direction: column;
  max-height: 90vh;
  animation: modalIn 0.3s ease-out;
}

.modal-header {
  padding: 16px 24px;
  /* 修改：底边框改为浅灰 */
  border-bottom: 1px solid #e2e8f0; 
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.modal-header h3 {
  margin: 0;
  /* 修改：标题改为深黑色 */
  color: #1e293b; 
  font-size: 1.1rem;
  font-weight: 600;
}

.close-btn {
  background: transparent;
  border: none;
  color: #94a3b8;
  cursor: pointer;
  font-size: 1.2rem;
  transition: color 0.2s;
}
/* 修改：关闭按钮悬停变深色，而不是白色 */
.close-btn:hover { color: #475569; } 

.modal-body {
  padding: 24px;
  overflow-y: auto;
  /* 修改：内容文字改为深灰色 */
  color: #334155; 
}

.modal-footer {
  padding: 16px 24px;
  /* 修改：顶边框改为浅灰 */
  border-top: 1px solid #e2e8f0; 
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  background-color: #f8fafc; /*以此区分底部区域，可选 */
  border-bottom-left-radius: 12px;
  border-bottom-right-radius: 12px;
}

.btn-cancel {
  padding: 8px 16px;
  background: #fff;
  /* 修改：取消按钮边框和文字颜色 */
  border: 1px solid #cbd5e1;
  color: #475569;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}
.btn-cancel:hover {
  background: #f1f5f9;
  border-color: #94a3b8;
  color: #1e293b;
}

.btn-confirm {
  padding: 8px 16px;
  background: #20ae7c;
  border: none;
  color: #fff;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.2s;
}
.btn-confirm:hover {
  background: #189e6e;
}

/* 动画 */
.fade-enter-active, .fade-leave-active { transition: opacity 0.3s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

@keyframes modalIn {
  from { transform: translateY(-20px); opacity: 0; }
  to { transform: translateY(0); opacity: 1; }
}
</style>