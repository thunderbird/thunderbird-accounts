<script setup>
import { computed, useTemplateRef } from 'vue';
import { TextInput, BrandButton, CheckboxInput, NoticeBar, NoticeBarTypes } from '@thunderbirdops/services-ui';
import { PhArrowRight } from '@phosphor-icons/vue';
import MessageBar from '@/vue/components/MessageBar.vue';
import ThunderbirdLogoLight from '@/svg/thunderbird-pro-light.svg';
import OrbGraphic from '@/images/orb-graphic.png';

const firstError = window._page.currentView?.firstError;
const formAction = window._page.currentView?.formAction;
const rememberMe = window._page.currentView?.rememberMe;
const forgotPasswordUrl = window._page.currentView?.forgotPasswordUrl;
const registerUrl = window._page.currentView?.registerUrl;
const supportUrl = window._page.currentView?.supportUrl;
const loginForm = useTemplateRef('login-form');

const onSubmit = () => {
  loginForm?.value?.submit();
};

const usernameError = computed(() => {
  return firstError ? '' : null;
});
const passwordError = computed(() => {
  return firstError ? '' : null;
});

</script>

<script>
export default {
  name: 'LoginView'
};
</script>

<template>
  <div class="login-view-container">
    <div class="login-view-card">
      <!-- Left side: Orb graphic -->
      <div class="left-side">
        <img :src="OrbGraphic" alt="Thunderbird Orb" class="orb-graphic" />
      </div>
      
      <!-- Right side: Login panel -->
      <div class="right-side">
        <notice-bar :type="NoticeBarTypes.Critical" v-if="firstError">{{ firstError }}</notice-bar>
        <message-bar v-else/>

        <a href="https://thunderbird.net" class="logo-link">
          <img :src="ThunderbirdLogoLight" alt="Thunderbird Pro" class="logo" />
        </a>
  
        <div>
          <h2 data-testid="header-text">{{ $t('loginAccountTitle') }}</h2>
          <form id="kc-form-login" ref="login-form" method="POST" :action="formAction" @submit.prevent="onSubmit"
                @keyup.enter="onSubmit">
            <div class="form-elements">
              <text-input
                data-testid="username-input"
                id="username"
                name="username"
                required
                autocomplete="username webauthn"
                autofocus
                :error="usernameError"
                outerSuffix="@thundermail.com"
              >
                {{ $t('email') }}
              </text-input>
              <text-input
                data-testid="password-input"
                id="password"
                name="password"
                required
                autocomplete="current-password"
                type="password"
                :error="passwordError"
              >
                {{ $t('password') }}
              </text-input>
            </div>

            <a
              v-if="forgotPasswordUrl"
              :href="forgotPasswordUrl"
              class="forgot-password-link"
            >
              {{ $t('doForgotPassword') }}
            </a>

            <checkbox-input data-testid="remember-me-input" name="keep-me-signed-in" :label="$t('rememberMe')" v-model="rememberMe"></checkbox-input>

            <div class="buttons">
              <brand-button data-testid="submit-btn" class="submit" @click="onSubmit">
                {{ $t('doLogIn') }}

                <template #iconRight>
                  <ph-arrow-right size="20" />
                </template>
              </brand-button>
            </div>
          </form>
          <div class="footer-link-container">
            <template v-if="registerUrl">
              <i18n-t keypath="goToRegister" tag="span">
                <a :href="registerUrl" data-testid="go-to-register-url">{{ $t('goToRegisterAction') }}</a>
              </i18n-t>

              •
            </template>
            <i18n-t keypath="needHelp" tag="span">
              <a :href="supportUrl" data-testid="go-to-support-url">{{ $t('needHelpAction') }}</a>
            </i18n-t>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.login-view-container {
  height: 100%;

  .login-view-card {
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    background-color: inherit;

    .right-side {
      position: relative;
      display: flex;
      flex-direction: column;
      padding: 2rem;
      background-color: var(--colour-neutral-base, #ffffff);

      .notice-bar {
        position: absolute;
        top: 1rem;
        left: 1.5rem;
        right: 1.5rem;
        z-index: 1;
      }

      .logo-link {
        display: block;
        margin-bottom: var(--space-24, 24px);
        text-decoration: none;
        margin-block-end: 2.8125rem;

        .logo {
          height: 36px;
          width: auto;
          transition: opacity 0.2s ease;

          &:hover {
            opacity: 0.8;
          }
        }
      }

      h2 {
        font-size: 2.25rem;
        font-family: metropolis;
        font-weight: normal;
        letter-spacing: -0.36px;
        line-height: 1.2;
        color: var(--colour-primary-default);
        margin: 0 0 1.5rem 0;
      }

      form {
        margin-block-end: 2.625rem;
      }

      .forgot-password-link {
        display: block;
        font-size: 0.6875rem;
        color: var(--colour-ti-muted);
        margin-block-end: 2rem;
      }

      .footer-link-container {
        display: flex;
        gap: 0.425rem;
        flex-wrap: wrap;
        justify-content: center;
        font-size: 0.75rem;
        color: var(--colour-ti-secondary);

        a {
          color: var(--colour-ti-secondary);
        }
      }

      .form-elements {
        display: flex;
        flex-direction: column;
        gap: 1.5rem;
        margin-bottom: 0.5rem;
      }

      .buttons {
        margin-top: var(--space-24);
        width: 100%;

        .submit {
          margin-right: 0;
          margin-left: auto;
        }
      }
    }
  }
}

.left-side {
  display: none;
}

.orb-graphic {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: contain;
}

@media (min-width: 640px) {
  .left-side {
    display: block;
    flex: 1;
    height: 100%;
  }

  .right-side {
    flex: 1;
  }
}

@media (min-width: 1280px) {
  .login-view-container {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100%;
    background-color: var(--colour-ti-base);

    .login-view-card {
      max-width: 1280px;
      max-height: 720px;
      border-radius: 2rem;
      align-items: initial;
      border: 0.0625rem solid var(--colour-neutral-border-intense);

      .right-side {
        border-radius: 0 2rem 2rem 0;
        padding: 6rem 10rem 5.625rem 6rem;
      }
    }
  }
}
</style>
