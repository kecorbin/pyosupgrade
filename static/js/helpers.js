function showmodal() {
    // Show modal for submitting upgrade jobs
    $('#newStagingModal').modal('show');

}

function showCredentialsModal() {
    // Show modal for gathering credentials
    $('#credentials').modal('show');

}
function submitCreds(url) {
    // called when credentials form is submitted
    var form = $(this)
    form.submit()
    $('#newStagingModal').modal('hide')
    //showProgress(form, url)

}
