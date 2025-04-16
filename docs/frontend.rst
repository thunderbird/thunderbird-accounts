==============================================
Frontend Development
==============================================

To ensure that our look and feel is consistent with other Thunderbird Services we utilize VueJS and our Services-UI library.

The intention here is to not make an SPA, but to enhance existing django templates in a language the team is comfortable working in.

Overview
--------

* Create the Single File Component (SFC)
* Import the SFC in `app.js` and specify the target DOM ID (i.e., the mount point)
* Either:
  * Update existing template, adding DOM ID
  * Or create a new url route, view function, and template (that contains DOM ID)
* If necessary, pass Django variables to the SFC

Creating the SFC
----------------

Create a new `.vue` file in `assets/app/vue/components/`

Create this as a standalone Vue component that does not rely on props or routing.


Adding the SFC to `app.js`
--------------------------

Import your Vue component into `app.js`.

Update the `vueApps` array with an object that specifies:
* the DOM ID mount point
* your new Vue component

.. code-block:: javascript
  import CheckoutFlow from '@/components/CheckoutFlow.vue';
  const vueApps = [
    {
      id: 'checkoutFlow',
      sfc: CheckoutFlow,
    },
  ]

With this change, your SFC will automatically get mounted if the DOM ID exists.


Add DOM ID to template
----------------------

If you are adding the SFC to an existing template, add the element where the SFC should be mounted:

.. code-block:: django
  {% extends 'mail/self-serve/_base.html' %}
  {% block page_heading %}
    <h2>Self Serve - Subscription</h2>
  {% endblock %}
  {% block body %}
    <div id="checkoutFlow"></div>
  {% endblock %}

Make sure to match the DOM ID specified in `app.js`

If you are creating a completely new page, you will need to create the URL route, the view function, and the template file.

Pass Django variables to SFC
----------------------------

If you need to supply the SFC with values from the Django application, do these two things:
1. Provide them to the template from the view function.
2. Add them to the `window._page` object in the template


This example renders `mail/self-serve/subscription.html` and provides context variables:
.. code-block:: python
  def self_serve_subscription(request: HttpRequest):
    """Subscription page allowing user to select plan tier and do checkout via Paddle.js overlay"""
    account = request.user.account_set.first()
    return TemplateResponse(
        request,
        'mail/self-serve/subscription.html',
        {
            'is_subscription': True,
            'success_redirect': reverse('self_serve_subscription_success'),
            'paddle_token': settings.PADDLE_TOKEN,
            'paddle_environment': settings.PADDLE_ENV,
            'paddle_price_id_lo': settings.PADDLE_PRICE_ID_LO,
            'paddle_price_id_md': settings.PADDLE_PRICE_ID_MD,
            'paddle_price_id_hi': settings.PADDLE_PRICE_ID_HI,
            **self_serve_common_options(False, account),
        },
    )

In the template, the context variables are attached to the `window` object:

.. code-block:: django
  {% extends 'mail/self-serve/_base.html' %}
  {% block page_heading %}
    <h2>Self Serve - Subscription</h2>
  {% endblock %}
  {% block body %}
    <div id="checkoutFlow"></div>
    <script>
      window._page.paddleToken="{{ paddle_token }}";
      window._page.paddleEnvironment="{{ paddle_environment}}";
      window._page.successRedirect="{{ success_redirect }}";
      window._page.paddlePriceIdLo="{{ paddle_price_id_lo }}";
      window._page.paddlePriceIdMd="{{ paddle_price_id_md }}";
      window._page.paddlePriceIdHi="{{ paddle_price_id_hi }}";
    </script>
  {% endblock %}


The SFC accesses and uses these values in the `<script setup>`:

.. code-block:: javascript
  import { ref, onMounted } from 'vue';
  import { initializePaddle } from '@paddle/paddle-js';

  const isLoading = ref(true);
  const priceItems = ref([]);

  const paddleToken = window._page.paddleToken;
  const paddleEnvironment = window._page.paddleEnvironment;
  const paddlePriceIdLo = window._page.paddlePriceIdLo;
  const paddlePriceIdMd = window._page.paddlePriceIdMd;
  const paddlePriceIdHi = window._page.paddlePriceIdHi;
  const successRedirect = window._page.successRedirect;



Mounting a SFC
--------------

If this is the first SFC used in the django application, you will need to write the JavaScript that mounts it to a DOM element.

In order to mount a SFC you will need to import the SFC, create a VueJS app and mount it to a specific div. Note this will replace everything in that div.

.. code-block:: javascript

  import MyComponent from "@/components/MyComponent.vue";
  const myComponentApp = createApp(MyComponent);
  myComponentApp.mount('#myComponentGoesHere');


