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
    console.log('鼠标在遮罩层按下')
  } else {
    isPressedOnOverlay.value = false
    console.log('鼠标在内容区按下 (准备复制/拖拽)')
  }
}

// 2. 鼠标抬起
const handleMouseUp = (e) => {
  // 只有当：起点是遮罩层 && 终点也是遮罩层，才关闭
  if (isPressedOnOverlay.value && e.target === e.currentTarget) {
    console.log('满足关闭条件 -> 关闭弹窗')
    emit('close')
  } else {
    console.log('不满足关闭条件 (可能是拖拽选中文本) -> 不关闭')
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
  background: rgba(0, 0, 0, 0.5); /* 半透明遮罩 */
  backdrop-filter: blur(3px);     /* 模糊背景 */
  z-index: 9999;
  display: flex;
  justify-content: center;
  align-items: center;
}

.modal-container {
  background: #1e293b; /* 深色背景 */
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5);
  display: flex;
  flex-direction: column;
  max-height: 90vh; /* 防止太高超出屏幕 */
  animation: modalIn 0.3s ease-out;
}

.modal-header {
  padding: 16px 24px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.modal-header h3 {
  margin: 0;
  color: #fff;
  font-size: 1.1rem;
}
.close-btn {
  background: transparent;
  border: none;
  color: #94a3b8;
  cursor: pointer;
  font-size: 1.2rem;
}
.close-btn:hover { color: #fff; }

.modal-body {
  padding: 24px;
  overflow-y: auto; /* 内容过多可滚动 */
  color: #cbd5e1;
}

.modal-footer {
  padding: 16px 24px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.btn-cancel {
  padding: 8px 16px;
  background: transparent;
  border: 1px solid rgba(255, 255, 255, 0.2);
  color: #fff;
  border-radius: 6px;
  cursor: pointer;
}
.btn-confirm {
  padding: 8px 16px;
  background: #20ae7c;
  border: none;
  color: #fff;
  border-radius: 6px;
  cursor: pointer;
}

/* 动画 */
.fade-enter-active, .fade-leave-active { transition: opacity 0.3s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

@keyframes modalIn {
  from { transform: translateY(-20px); opacity: 0; }
  to { transform: translateY(0); opacity: 1; }
}
</style>