<script setup>
const year = new Date().getFullYear()
</script>

<template>
  <footer class="footer">
    <div class="container">
      <div class="row">
        <div class="col-md-6">
          <h5><i class="bi bi-house-heart-fill"></i> ApartBook</h5>
          <p class="text-muted">{{ $t('footer.tagline') }}</p>
        </div>
        <div class="col-md-6 text-md-end">
          <p class="text-muted">&copy; {{ year }} ApartBook. {{ $t('footer.rights') }}</p>
        </div>
      </div>
    </div>
  </footer>
</template>
