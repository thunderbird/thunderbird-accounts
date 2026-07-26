<#import "template.ftl" as layout>
<@layout.registrationLayout displayInfo=false; section>
<#if section = "js">
    <script>
      window._page['currentView'] = {
        formAction: '${url.loginAction}',
        authenticationSelections: [
          //<#list auth.authenticationSelections as selection>
          {
            execId: '${selection.authExecId}',
            key: '${selection.displayName?js_string}',
            displayName: '${msg('${selection.displayName}')?js_string}',
            helpText: '${msg('${selection.helpText}')?js_string}',
          },
          //</#list>
        ],
      };
      window._l10n = {
        ...window._l10n,
        loginChooseAuthenticator: '${msg("loginChooseAuthenticator")?js_string}',
      };
    </script>
    </#if>
</@layout.registrationLayout>
