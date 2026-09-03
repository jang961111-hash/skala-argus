<script setup>
import { ref } from 'vue'

// 제품 사진. 서버는 320px 썸네일(thumbnailUrl)과 원본(originalUrl) URL 을 따로 내려준다 (계약 §4-9).
defineProps({
  photos: { type: Array, default: () => [] },
  title: { type: String, default: '제품 사진' },
})

const lightbox = ref(null)
const openable = (p) => Boolean(p.originalUrl || p.thumbnailUrl)
function open(p) {
  if (openable(p)) lightbox.value = p
}
const fmtSize = (n) => (n >= 1048576 ? `${(n / 1048576).toFixed(1)}MB` : `${Math.max(1, Math.round(n / 1024))}KB`)
</script>

<template>
  <div class="stack">
    <label>{{ title }} ({{ photos.length }})</label>
    <p v-if="!photos.length" class="muted small">첨부된 사진이 없습니다.</p>
    <div v-else class="strip">
      <figure
        v-for="p in photos"
        :key="p.id"
        class="thumb"
        :class="{ clickable: openable(p) }"
        @click="open(p)"
      >
        <img v-if="p.thumbnailUrl" :src="p.thumbnailUrl" :alt="p.fileName" />
        <span v-else class="placeholder">📷</span>
        <figcaption class="small">{{ p.fileName }}<br /><span class="muted">{{ fmtSize(p.size) }}</span></figcaption>
      </figure>
    </div>

    <div v-if="lightbox" class="modal-backdrop" @click="lightbox = null">
      <div class="modal card" @click.stop>
        <div class="row between" style="margin-bottom: 10px">
          <strong>{{ lightbox.fileName }}</strong>
          <button class="sm" @click="lightbox = null">닫기</button>
        </div>
        <img :src="lightbox.originalUrl || lightbox.thumbnailUrl" :alt="lightbox.fileName" class="full" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.strip { display: flex; flex-wrap: wrap; gap: 10px; }
.thumb {
  margin: 0; width: 120px; border: 1px solid var(--border); border-radius: 8px;
  overflow: hidden; background: var(--surface);
}
.thumb.clickable { cursor: zoom-in; }
.thumb img { width: 100%; height: 84px; object-fit: cover; display: block; }
.placeholder {
  display: flex; align-items: center; justify-content: center; height: 84px; font-size: 26px; background: #f0f2f5;
}
figcaption { padding: 6px 8px; word-break: break-all; }
.full { width: 100%; border-radius: 8px; }
</style>
