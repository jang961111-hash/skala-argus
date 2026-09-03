<script setup>
import GnbBase from './GnbBase.vue'
import { ROLE_LABEL, ROLE } from '../constants/domain'

// 화면정의서 v2.0: 엔지니어 GNB — 홈 / 요청 등록 / 내 요청
const TABS = [
  { to: '/home', label: '홈' },
  { to: '/requests/new', label: '요청 등록' },
  { to: '/my/requests', label: '내 요청' },
]
</script>

<template>
  <GnbBase :role-label="ROLE_LABEL[ROLE.ENGINEER]" :tabs="TABS" />
</template>
