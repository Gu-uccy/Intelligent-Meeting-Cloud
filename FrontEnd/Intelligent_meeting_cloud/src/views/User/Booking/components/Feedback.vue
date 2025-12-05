<script setup>
import { ref, onMounted } from 'vue';
import { reportFault } from "@/apis/fault";
import { getUserRoomPage } from "@/apis/room";
import { toast } from '@/utils/message'
import '@/styles/el-message.css' 

const form = ref({ roomName: '', type: 'hardware', content: '' });
const roomOptions = ref([]);

const fetchRoomsForSelect = async () => {
  try {
    const res = await getUserRoomPage({ page: 1, pageSize: 50 });
    if(res.data && res.data.records) {
      roomOptions.value = res.data.records.map(r => ({
        id: r.id,
        name: `${r.roomCode} ${r.location || ''}`
      }));
    }
  } catch(e) {}
};

const submit = async () => {
  if (!form.value.content || !form.value.roomName) return toast.warning('请完善信息');
  
  const target = roomOptions.value.find(r => r.name === form.value.roomName);
  const payload = {
    deviceName: form.value.type,
    faultDesc: form.value.content,
    roomId: target ? target.id : null 
  };
  
  try {
    await reportFault(payload);
    toast.success('反馈成功');
    form.value.content = '';
  } catch (e) { toast.error('提交失败'); }
};

onMounted(fetchRoomsForSelect);
</script>

<template>
  <div class="view-feedback">
    <div class="form-container">
      <h3 class="form-title">提交问题或建议</h3>
      
      <div class="form-group">
        <label>涉及会议室</label>
        <select v-model="form.roomName">
          <option value="" disabled selected>请选择会议室</option>
          <option v-for="r in roomOptions" :key="r.id" :value="r.name">{{ r.name }}</option>
        </select>
      </div>

      <div class="form-group">
        <label>问题类型</label>
        <div class="radio-group">
          <label class="radio-card" :class="{active: form.type === 'hardware'}">
            <input type="radio" value="hardware" v-model="form.type" hidden>
            <i class="fa-solid fa-computer"></i> 硬件故障
          </label>
          <label class="radio-card" :class="{active: form.type === 'software'}">
            <input type="radio" value="software" v-model="form.type" hidden>
            <i class="fa-solid fa-wifi"></i> 软件/网络
          </label>
          <label class="radio-card" :class="{active: form.type === 'clean'}">
            <input type="radio" value="clean" v-model="form.type" hidden>
            <i class="fa-solid fa-broom"></i> 卫生问题
          </label>
        </div>
      </div>

      <div class="form-group">
        <label>详细描述</label>
        <textarea v-model="form.content" rows="4" placeholder="请描述具体问题..."></textarea>
      </div>
      
      <button class="btn-submit" @click="submit">提交反馈</button>
    </div>
  </div>
</template>

<style scoped>
.view-feedback { 
  display: flex; 
  justify-content: center; 
  height: 100%; 
}
.form-container { 
  width: 100%; 
  max-width: 500px; 
  padding-top: 2rem; 
}
.form-title { 
  margin-bottom: 1.5rem; 
  color: #fff; 
}

/* --- 表单元素 --- */
.form-group { margin-bottom: 1.5rem; }
.form-group label { 
  display: block; margin-bottom: 0.5rem; 
  font-weight: 600; color: #cbd5e1; font-size: 0.9rem; 
}
.form-group select, 
.form-group textarea, 
.form-group input { 
  width: 100%; padding: 0.8rem; 
  border: 1px solid rgba(255, 255, 255, 0.1); 
  border-radius: 8px; outline: none; 
  background: rgba(0, 0, 0, 0.2); color: white; 
  box-sizing: border-box; 
}

.form-group select option { background: #1e293b; color: white; }
.form-group textarea:focus, 
.form-group input:focus, 
.form-group select:focus { border-color: #20ae7c; }

/* --- 单选卡片组 --- */
.radio-group { display: flex; gap: 1rem; }
.radio-card { 
  flex: 1; border: 1px solid rgba(255, 255, 255, 0.1); 
  padding: 1rem; border-radius: 8px; text-align: center; 
  cursor: pointer; color: #94a3b8; transition: all 0.2s; 
  background: rgba(0, 0, 0, 0.2);
}
.radio-card:hover { border-color: #20ae7c7d; background: #20ae7c0e;}
.radio-card.active { 
  background: #20ae7c1c;
  border-color: #20ae7c;
  color: #00ffa6;
}

.btn-submit { 
  width: 100%; padding: 1rem; background: #20ae7cc4; 
  color: white; border: none; border-radius: 8px; 
  font-weight: 600; cursor: pointer; transition: all 0.3s; 
}
.btn-submit:hover { background-color: #20ae7c; }
</style>