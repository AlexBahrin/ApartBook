<script setup>
import { RouterLink } from 'vue-router'
</script>

<template>
  <div class="container py-5 text-center">
    <h1 class="display-1 fw-bold text-primary">404</h1>
    <h3>{{ $t('notFound.title') }}</h3>
    <p class="text-muted">{{ $t('notFound.message') }}</p>
    <RouterLink :to="{ name: 'landing' }" class="btn btn-primary">{{ $t('notFound.home') }}</RouterLink>
  </div>
</template>
