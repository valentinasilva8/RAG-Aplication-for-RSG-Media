create table
  public.documents (
    document_id serial not null,
    filename text not null,
    constraint documents_pkey primary key (document_id),
    constraint documents_filename_key unique (filename)
  ) tablespace pg_default;