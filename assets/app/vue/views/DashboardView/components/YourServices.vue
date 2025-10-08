<template>
  <h2>Your Services</h2>

  <div class="your-services-card">
    <a class="service-icon-link" href="#">
      <img src="@/assets/svg/thundermail-icon.svg" alt="Thundermail Logo" />
      <p>Thundermail</p>
    </a>

    <a class="service-icon-link" href="#">
      <img src="@/assets/svg/thundermail-icon.svg" alt="Appointment Logo" />
      <p>Appointment</p>
    </a>

    <a class="service-icon-link" href="#">
      <img src="@/assets/svg/thundermail-icon.svg" alt="Send Logo" />
      <p>Send</p>
    </a>
  </div>
</template>

<style scoped>
h2 {
  font-family: metropolis;
  font-size: 0.875rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.42px;
  margin-block-end: 1rem;
  color: var(--colour-ti-secondary);
}

.your-services-card {
  display: flex;
  gap: 0.5rem;
  border-radius: 1.5rem;
  box-shadow: inset 2px 2px 4px 0 rgba(0, 0, 0, 0.05), 1px 1px 0 0 rgba(255, 255, 255, 0.6);
  background-color: rgba(228, 228, 231, 0.5);
  padding: 1.5rem 2rem;

  .service-icon-link {
    display: flex;
    flex-direction: column;
    align-items: center;
    text-decoration: none;

    p {
      font-size: 0.625rem;
      font-weight: 600;
      font-family: metropolis;
      letter-spacing: 0.3px;
      line-height: 1.2;
      color: var(--colour-ti-secondary);
    }
  }
}
</style>