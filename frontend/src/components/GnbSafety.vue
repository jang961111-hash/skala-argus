<script setup>
import GnbBase from './GnbBase.vue'
import { ROLE_LABEL, ROLE } from '../constants/domain'

// 화면정의서 v2.0: 안전관리자 GNB — 요청 관리 / 처리 이력
const TABS = [
  { to: '/manage/requests', label: '요청 관리' },
  { to: '/manage/history', label: '처리 이력' },
]
</script>

<template>
  <GnbBase :role-label="ROLE_LABEL[ROLE.SAFETY_MANAGER]" :tabs="TABS" />
</template>
