-- Create sample accounts
INSERT INTO Users (id, tag, description, password_hash, is_admin) VALUES (0, "admin", "he who remains", "pbkdf2:sha256:260000$XS17YryLSAEyWSHI$fda8a17aad0e9acc877b39ddbee52afeadb9405692e5a9843bc73d0ad1388e85", 1);
INSERT INTO Users (id, tag, description, password_hash, is_admin) VALUES (1, "testguy", "tester", "pbkdf2:sha256:260000$XS17YryLSAEyWSHI$fda8a17aad0e9acc877b39ddbee52afeadb9405692e5a9843bc73d0ad1388e85", 0);
