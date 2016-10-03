/*
 * Copyright 2013 Red Hat Inc., Durham, North Carolina.
 * All Rights Reserved.
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 * Authors:
 *      Martin Preisler <mpreisle@redhat.com>
 */

#ifndef SCAP_WORKBENCH_SSG_INTEGRATION_DIALOG_H_
#define SCAP_WORKBENCH_SSG_INTEGRATION_DIALOG_H_

#include "ForwardDecls.h"

#include <QDialog>

extern "C"
{
#include <xccdf_benchmark.h>
}

#include "ui_SSGIntegrationDialog.h"

class SSGIntegrationDialog : public QDialog
{
    Q_OBJECT

    public:
        explicit SSGIntegrationDialog(QWidget* parent = 0);
        virtual ~SSGIntegrationDialog();

        void setDismissLabel(const QString& label);

        const QString& getSelectedSSGFile() const;
        bool loadOtherContentSelected();

        static bool isSSGAvailable();

    private slots:
        void loadContent();

    private:
        void scrapeSSGVariants();

        Ui_SSGIntegrationDialog mUI;
        QString mSelectedSSGFile;
        bool loadOtherContent;
};

#endif
