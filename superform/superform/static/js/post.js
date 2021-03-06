$("input[type='checkbox']").each(function(){

    let mod = $(this).attr("module-namechan").split('.')[2];
    if(mod != undefined){
        if(post_form_validations[mod]['image_type'] != undefined && post_form_validations[mod]['image_type'].toLocaleLowerCase() =="url"){
             $(this).on("click",adapt_post_to_channel($(this).attr('data-namechan')));
        }
    }
});

function adapt_post_to_channel(chan_name){
    document.getElementById(chan_name+"_imagepost").type = "text";
}

$("#publish-button").click(function(event){
    var toReturn = true;
     $("input[type='checkbox']:checked").each(function(){
         let mod = $(this).attr("module-namechan").split('.')[2];
         let title_max_length=100000;
         let descr_max_length=100000;
         if(mod != undefined){
             console.log(post_form_validations[mod]);
             if(post_form_validations[mod]['title_max_length'] != undefined){
                 title_max_length = post_form_validations[mod]['title_max_length'] ;
             }
             if(post_form_validations[mod]['description_max_length'] != undefined){
                 descr_max_length = post_form_validations[mod]['description_max_length'] ;
             }
         }

        if((!prevalidate_post($(this).attr("data-namechan"),title_max_length,descr_max_length))){
            document.getElementById("li_"+$(this).attr("data-namechan")).children[0].style.color = "red";
            toReturn = false;
            return toReturn;
        }

      });
     return toReturn;
});


function createErrorMessage (element,error_message,id){
    var message = document.getElementById(id);
    if(message) {
        message.textContent =  error_message;
        message.hidden = false;
    }else{
        var new_elem = document.createElement('div');
        new_elem.setAttribute('id', id);
        new_elem.setAttribute('class',"error");
        var t = document.createTextNode(error_message);
        new_elem.appendChild(t);
         element.before(new_elem);
    }
}
function prevalidate_post (chan_name,title_length,descr_length){
     var toReturn = true;
     var elementToRemove;
     var input_title = document.getElementById(chan_name+"_titlepost");
    if (input_title.value == "") {
        createErrorMessage(input_title,"the title is empty","error_title");
        input_title.classList.add("invalid");
        toReturn = false;
    }else if(input_title.value.length > title_length){
         createErrorMessage(input_title,"the title is too long","error_title");
        input_title.classList.add("invalid");
        toReturn = false;
    }else{
        elementToRemove = document.getElementById("error_title");;
        if(elementToRemove){
            elementToRemove.hidden = true;
        }
        input_title.classList.remove("invalid");
    }
    var input_descrip = document.getElementById(chan_name+"_descriptionpost");
    if (input_descrip.value == "") {
        createErrorMessage(input_descrip,"the description is empty","error_desc");
        input_descrip.classList.add("invalid");
        toReturn = false;
    }else if(input_descrip.value.length > descr_length){
        createErrorMessage(input_descrip,"the description is too long","error_desc");
        input_descrip.classList.add("invalid");
        toReturn = false;
    }else{
        elementToRemove = document.getElementById("error_desc");
        if(elementToRemove){
            elementToRemove.hidden = true;
        }
        input_descrip.classList.remove("invalid");
    }

    var input_linkUrlPost = document.getElementById(chan_name+"_linkurlpost");
    var pattern = new RegExp('^(?:(?:https?|http?|wwww?):\\/\\/)?(?:(?!(?:10|127)(?:\\.\\d{1,3}){3})(?!(?:169\\.254|192\\.168)(?:\\.\\d{1,3}){2})(?!172\\.(?:1[6-9]|2\\d|3[0-1])(?:\\.\\d{1,3}){2})(?:[1-9]\\d?|1\\d\\d|2[01]\\d|22[0-3])(?:\\.(?:1?\\d{1,2}|2[0-4]\\d|25[0-5])){2}(?:\\.(?:[1-9]\\d?|1\\d\\d|2[0-4]\\d|25[0-4]))|(?:(?:[a-z\u00a1-\uffff0-9]-*)*[a-z\u00a1-\uffff0-9]+)(?:\\.(?:[a-z\u00a1-\uffff0-9]-*)*[a-z\u00a1-\uffff0-9]+)*(?:\\.(?:[a-z\u00a1-\uffff]{2,})))(?::\\d{2,5})?(?:\\/\\S*)?$');
    if( input_linkUrlPost.value != "" && !pattern.test(input_linkUrlPost.value)) {
        createErrorMessage(input_linkUrlPost,"insert a valid link","error_linkUrlPost");
        input_linkUrlPost.classList.add("invalid");
        toReturn = false;
    }else{
        elementToRemove = document.getElementById("error_linkUrlPost");
        if(elementToRemove){
            elementToRemove.hidden = true;
        }
         input_linkUrlPost.classList.remove("invalid");
    }

    var input_linkImgUrlPost = document.getElementById(chan_name+"_imagepost");
    if( input_linkImgUrlPost.value != "" && !pattern.test(input_linkImgUrlPost.value)) {
        createErrorMessage(input_linkImgUrlPost,"insert a valid picture link ","error_linkImgUrlPost");
        input_linkImgUrlPost.classList.add("invalid");
        toReturn = false;
    }else{
        elementToRemove = document.getElementById("error_linkImgUrlPost");
        if(elementToRemove){
            elementToRemove.hidden = true;
        }
         input_linkImgUrlPost.classList.remove("invalid");
    }

    var input_datefrompost = document.getElementById(chan_name+"_datefrompost");
    if(input_datefrompost.value == ""){
        createErrorMessage(input_datefrompost,"the date from post is empty","error_datefrompost");
        input_datefrompost.classList.add("invalid");
        toReturn = false;
    }else{
        elementToRemove = document.getElementById("error_datefrompost");
        if(elementToRemove){
            elementToRemove.hidden = true;
        }
        input_datefrompost.classList.remove("invalid");
    }

    var input_dateuntilpost = document.getElementById(chan_name+"_dateuntilpost");
    if(input_dateuntilpost.value == ""){
        createErrorMessage(input_dateuntilpost,"the date until post is empty","error_dateuntilpost");
        input_dateuntilpost.classList.add("invalid");
        toReturn = false;
    }else{
        elementToRemove = document.getElementById("error_dateuntilpost");
        if(elementToRemove){
            elementToRemove.hidden = true;
        }
        input_dateuntilpost.classList.remove("invalid");
    }
    if(input_datefrompost.value != "" && input_dateuntilpost.value != "") {
        var a = new Date(input_datefrompost.value);
        var b = new Date(input_dateuntilpost.value);

        if (b < a) {
            createErrorMessage(input_dateuntilpost, "the date until post is greater that date from post", "error_dateuntilpost");
            input_dateuntilpost.classList.add("invalid");
            toReturn = false;
        } else {
            elementToRemove = document.getElementById("error_dateuntilpost");
            if (elementToRemove) {
                elementToRemove.hidden = true;
            }
            input_dateuntilpost.classList.remove("invalid");
        }
    }
    return toReturn;
}

