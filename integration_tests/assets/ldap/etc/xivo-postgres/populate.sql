INSERT INTO "tenant" (uuid) VALUES ('4a037de3-94bd-4d40-b4d1-3fc09184c3d2') ON CONFLICT DO NOTHING;
INSERT INTO "entity" ("id", "name", "displayname", "tenant_uuid", "description") VALUES (1, 'default', 'Default', '4a037de3-94bd-4d40-b4d1-3fc09184c3d2', '');
INSERT INTO "func_key_template" (private) VALUES (TRUE);
INSERT INTO "userfeatures" (uuid, firstname, email, description, func_key_private_template_id, entityid, tenant_uuid)
VALUES
(1, 'Alice', 'awonderland@wazo-auth.com', '', 1, 1, '4a037de3-94bd-4d40-b4d1-3fc09184c3d2');
