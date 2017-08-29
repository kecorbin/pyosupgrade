function showmodal() {
    // Show modal for gathering credentials
    $('#newUpgradeModal').modal('show');

}

function submitCreds(url) {
    // called when credentials form is submitted
    var form = $(this)
    form.submit()
    $('#newUpgradeModal').modal('hide')
    //showProgress(form, url)

}
