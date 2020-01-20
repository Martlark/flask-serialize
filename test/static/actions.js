$(".index-delete").click(data => {
    const id = $(data.target).data("id");
    $.ajax(`/setting_delete/${id}`, {method: "delete",}
    ).then(() => location.reload()
    ).fail((xhr, textStatus, errorThrown) =>
        alert(`${xhr.responseText}`)
    );

});

$(".sub-setting-delete").click(data => {
    const id = $(data.target).data("id");
    $.ajax(`/sub_setting_delete/${id}`, {method: "delete",}
    ).then(() => location.reload()
    ).fail((xhr, textStatus, errorThrown) =>
        alert(`${xhr.responseText}`)
    );
});

function serialize(f) {
    let s = [];

    $("input", f).each((index, item) => {
        const name = $(item).attr("name");
        if (name) {
            let value = $(item).val();
            switch ($(item).attr("type")) {
                case "checkbox":
                    value = $(item).prop("checked") ? "true" : "false";
                    break;
                default:
                    break;
            }
            s.push(`${encodeURIComponent(name)}=${encodeURIComponent(value)}`);
        }
    });
    return s.join("&");
}

$(".sub-setting-edit").submit(data => {
    const $target = $(data.target);
    const id = $target.data("id");
    data.preventDefault();
    let form_data = serialize($target);
    $.ajax(`/sub_setting_put/${id}`, {method: "put", data: form_data}
    ).then((data) => {
            $("input[name=flong]", $target).val(data.properties.flong);
            $("input[name=boolean]", $target).prop("checked", data.properties.boolean);
        }
    ).fail((xhr, textStatus, errorThrown) =>
        alert(`${xhr.responseText}`)
    );

});


$(".random-value").each((index, item) => {
    $(item).val(Math.random().toString(36).substring(2, 7))
});

