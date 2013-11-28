var camus = camus || {};
camus.modules = camus.modules || {};


camus.gather_modules = function() {
  $('[data-camus-module]').each(function (index, element) {
    var name = $(element).attr("data-camus-module");
    var option_attr = $(element).attr("data-camus-options");
    var options = {}
    if (option_attr) {
      options = JSON.parse(option_attr);
    }

    if (name === undefined){
      throw new Error("need to supply value for data-camus-module");
    }
    module = camus.modules[name];
    if (module === undefined){
       throw new Error("No camus module named " + name);
    }
    module.init({}, options)
    ko.applyBindings(module, element);
  })
}


camus.modules.persona = {
    init: function(context, options) {
        console.log(options)
        if (!options.user_email){
            this.user_email = null;
        } else {
            this.user_email = options.user_email;
        };
        navigator.id.watch({
            loggedInUser: this.user_email,
            onlogin: function(assertion) {
              // A user has logged in! Here you need to:
              // 1. Send the assertion to your backend for verification and to create a session.
              // 2. Update your UI.
                $.ajax({ /* <-- This example uses jQuery, but you can use whatever you'd like */
                    type: 'POST',
                    url: '/persona/login', // This is a URL on your website.
                    data: {assertion: assertion},
                    success: function(res, status, xhr) { window.location.reload(); },
                    error: function(xhr, status, err) {
                        navigator.id.logout();
                        alert("Login failure: " + err);
                    }
                });
            },
            onlogout: function() {
              // A user has logged out! Here you need to:
              // Tear down the user's session by redirecting the user or making a call to your backend.
              // Also, make sure loggedInUser will get set to null on the next page load.
              // (That's a literal JavaScript null. Not false, 0, or undefined. null.)
                $.ajax({
                    type: 'POST',
                    url: '/persona/logout', // This is a URL on your website.
                    success: function(res, status, xhr) { window.location.reload(); },
                    error: function(xhr, status, err) { alert("Logout failure: " + err); }
                });
            }
        });
    }
}

$(function() {
  camus.gather_modules();
})
