function removerEvento(evento_id) {
    if (confirm("Tem certeza de que deseja remover este evento?")) {
        const form = document.createElement('form');
        form.method = 'post';
        form.action = '/remover_evento/' + evento_id;

        const hiddenField = document.createElement('input');
        hiddenField.type = 'hidden';
        hiddenField.name = 'evento_id';
        hiddenField.value = evento_id;

        form.appendChild(hiddenField);

        document.body.appendChild(form);
        form.submit();
    }
}