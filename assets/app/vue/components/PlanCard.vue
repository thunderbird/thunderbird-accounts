<template>
  <div class="plan-card">
    <div class="left">
      <h3>Early Bird Plan</h3>
      <p>Our initial offering, ideal for most users</p>
      <h4>
        <span class="price">$6</span>
        <span>per month<br>paid annually</span>
      </h4>
    </div>

    <ul>
      <li><strong>30 GB</strong> of Mail Storage</li>
      <li><strong>1</strong> Inbox, <strong>15</strong> Email addresses</li>
      <li><strong>3</strong> Custom Domains</li>
      <li><strong>60 GB</strong> of Send Storage</li>
    </ul>
  </div>
</template>

<style scoped>
.plan-card {
  display: flex;
  flex-direction: row;
  justify-content: flex-start;
  align-items: center;
  gap: 2rem;
  padding: 1.25rem;
  border-radius: 24px;
  border: solid 1px rgba(88, 201, 255, 0.2);
  background-color: var(--colour-ti-base);

  .left {
    display: flex;
    flex-direction: column;
    justify-content: flex-start;
    align-items: stretch;
    gap: 1rem;
    padding: 1.5rem 1rem;
    border-radius: 12px;
    background-image: linear-gradient(150deg, #131c28 30%, #0b1017);
    text-align: center;
    color: #f3f9fcf3;
    max-width: 12rem;

    h3 {
      background-image: linear-gradient(137deg, #58c9ff 47%, #ddb4fe 72%);
      font-family: Metropolis;
      font-size: 1.5rem;
      font-weight: 500;
      background-clip: text;
      color: transparent;
    }

    h4 {
      font-family: 'Inter', sans-serif;
      font-size: 0.75rem;
      line-height: 1;
      letter-spacing: normal;
      display: inline-flex;
      flex-direction: row;
      justify-content: center;
      font-weight: normal;
      gap: 0.375rem;

      span {
        text-align: left;
      }

      span.price {
        font-family: 'Metropolis', sans-serif;
        font-size: 1.2rem;
      }

      strong {
        font-size: 2rem;
        font-family: 'Metropolis', sans-serif;
      }
    }

    p {
      font-size: 0.875rem;
      line-height: 1.23;
    }
  }

  ul {
    flex-grow: 1;

    li {
      color: #ffffff;
      padding-block: 0.75rem;

      strong {
        font-weight: 600;
      }
    }

    li + li {
      border-block-start: 1px solid #58c9ff33;
    }
  }
}
</style>
