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

function updateAction() {
    var selectedEventId = document.getElementById('evento_id').value;
    var form = document.querySelector('form');
    form.action = "{{ url_for('inscrever_evento', evento_id='') }}" + selectedEventId;
}
// Atualizar a ação inicialmente
updateAction();