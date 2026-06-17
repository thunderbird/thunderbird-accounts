<template>
  <div class="plan-card">
    <div class="left">
      <h3>Early Bird Plan</h3>
      <p>Our initial offering, ideal for most users</p>
      <h4>
        <sup>$</sup>6
        <span>per month,<br>paid annually</span>
      </h4>
    </div>

    <ul>
      <li>
        <p><strong>30 GB</strong> of Mail Storage</p>
        <p><strong>1</strong> Inbox, <strong>15</strong> Email addresses</p>
        <p><strong>3</strong> Custom Domains</p>
        <p><strong>60 GB</strong> of Send Storage</p>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.plan-card {
  display: flex;
  flex-direction: row;
  justify-content: flex-start;
  align-items: center;
  gap: 32px;
  padding: 1.25rem;
  border-radius: 24px;
  border: solid 1px rgba(88, 201, 255, 0.2);
  background-color: var(--colour-ti-base);

  .left {
    display: flex;
    flex-direction: column;
    justify-content: flex-start;
    align-items: stretch;
    gap: 16px;
    padding: 1.5rem 1rem;
    border-radius: 12px;
    background-image: linear-gradient(150deg, #131c28 30%, #0b1017);
    text-align: center;
    color: #f3f9fcf3;

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
      font-weight: 500;
      line-height: 1;
      letter-spacing: normal;
      display: inline-flex;
      flex-direction: row;
      gap: 0.375rem;

      strong {
        font-size: 2rem;
        font-family: 'Metropolis', sans-serif;
        font-weight: normal;
      }
    }

    p {
      font-size: 0.875rem;
      line-height: 1.23;
    }
  }

  ul {
    li {
      color: #ffffff;

      p {
        padding-block: 0.75rem;

        strong {
          font-weight: 600;
        }
      }
    }

    li + li {
      p {
        border-block-start: 1px solid #58c9ff33;
      }
    }
  }
}
</style>
